"""Put the two sides together: what the report says (tone) against what the numbers show (trend)."""
import json
import os
import statistics
import time

from . import tone as T
from .trend import trend_from_dataset

DEFAULT_CACHE = os.path.join(os.environ.get("RAG_STORE_DIR", "rag_store"), "detector.json")
GAP_FLAG = 1.0          # how many 'standard deviations' apart the two scores must be to raise a flag


def analyse_company(ticker, rag, scorer, dataset_path, per_side=3):
    sents = T.select_sentences(rag, ticker)
    scores = scorer.score([s["text"] for s in sents]) if sents else []
    rows = [dict(s, **sc, net=sc["pos"] - sc["neg"]) for s, sc in zip(sents, scores)]
    trend = trend_from_dataset(ticker, dataset_path)
    best = sorted(rows, key=lambda r: -r["net"])[:per_side]
    worst = sorted(rows, key=lambda r: r["net"])[:per_side]
    fmt = lambda r: {"page": r["page"], "text": r["text"], "net": round(r["net"], 3)}
    return {
        "ticker": ticker, "sentences": len(rows), "tone": T.tone_of(scores),
        "positive_share": (sum(1 for r in rows if r["pos"] > max(r["neg"], r["neu"])) / len(rows)) if rows else None,
        "negative_share": (sum(1 for r in rows if r["neg"] > max(r["pos"], r["neu"])) / len(rows)) if rows else None,
        "trend": trend, "most_positive": [fmt(r) for r in best], "most_negative": [fmt(r) for r in worst],
    }


def _z(values):
    sd = statistics.pstdev(values) if len(values) > 1 else 0
    mu = statistics.mean(values) if values else 0
    return [(v - mu) / sd if sd > 1e-9 else 0.0 for v in values]


def add_verdicts(companies, gap_flag=GAP_FLAG):
    """Compare each company with the others. A report's tone is usually upbeat, so we judge the *gap* between
    its tone and its trend after putting both on the same scale across the companies."""
    ready = [c for c in companies if c.get("tone") is not None and (c.get("trend") or {}).get("score") is not None]
    zt, zs = _z([c["tone"] for c in ready]), _z([c["trend"]["score"] for c in ready])
    for c, a, b in zip(ready, zt, zs):
        gap = a - b
        c["tone_z"], c["trend_z"], c["gap"] = round(a, 2), round(b, 2), round(gap, 2)
        if len(ready) < 3:
            c["verdict"] = "not_enough_companies"
        elif gap >= gap_flag:
            c["verdict"] = "says_more_than_shows"
        elif gap <= -gap_flag:
            c["verdict"] = "shows_more_than_says"
        else:
            c["verdict"] = "consistent"
    for c in companies:
        c.setdefault("verdict", "not_enough_data")
    return companies


def save(companies, path=None, model="ProsusAI/finbert"):
    path = path or DEFAULT_CACHE
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"computed_at": int(time.time()), "model": model, "companies": companies}, f)


def load(path=None):
    path = path or DEFAULT_CACHE
    if not os.path.exists(path):
        raise FileNotFoundError("The Say vs. Show analysis has not been run yet. Run: python scripts/run_detector.py")
    with open(path, encoding="utf-8") as f:
        return json.load(f)
