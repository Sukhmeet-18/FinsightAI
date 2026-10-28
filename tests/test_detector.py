import os
import sys

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))
from backend.detector import router as det_router, service, tone, trend      # noqa: E402
from backend.rag import ingest, store                                         # noqa: E402
from backend.rag.service import RagService                                    # noqa: E402
from test_rag import HashEmbedder, StubLLM                                    # noqa: E402


class StubScorer:
    """Pretends to be FinBERT: sentences with 'grew' are positive, 'fell' negative, the rest neutral."""
    name = "stub-finbert"

    def score(self, sentences):
        out = []
        for s in sentences:
            if "grew" in s or "strong" in s:
                out.append({"pos": 0.9, "neg": 0.05, "neu": 0.05})
            elif "fell" in s or "weak" in s:
                out.append({"pos": 0.05, "neg": 0.9, "neu": 0.05})
            else:
                out.append({"pos": 0.1, "neg": 0.1, "neu": 0.8})
        return out


def make_csv(path):
    rows = []
    # trend up: UPCO, flat: FLATCO, down: DOWNCO, plus noise companies
    spec = {"UPCO": [(0.15, 0.10, 0.12), (0.18, 0.13, 0.17), (0.20, 0.16, 0.22)],
            "FLATCO": [(0.0, 0.10, 0.12), (0.0, 0.10, 0.12), (0.0, 0.10, 0.12)],
            "DOWNCO": [(0.02, 0.15, 0.20), (-0.03, 0.12, 0.15), (-0.08, 0.08, 0.10)],
            "TWOCO": [(None, 0.10, 0.10), (None, 0.12, 0.13), (0.1, 0.12, 0.13)]}
    for t, vals in spec.items():
        for i, (g, m, r) in enumerate(vals):
            rows.append({"ticker": t, "period": f"{2023 + i}-03-31", "revenue_growth": g, "profit_margin": m, "roe": r})
    rows.append({"ticker": "UPCO", "period": "2024-12-31", "revenue_growth": 9.9, "profit_margin": 9.9, "roe": 9.9})   # not a March year-end: ignored
    pd.DataFrame(rows).to_csv(path, index=False)


def test_sentence_splitting_keeps_prose_only():
    text = ("Revenue grew strongly during the year because of higher demand across all our segments. "
            "Total 1,234 5,678 9,012 3,456 7,890 1,111 2,222 3,333 4,444. "
            "Short one. "
            "Notice is hereby given that the thirtieth annual general meeting of the company will be held shortly. "
            "We remain cautious about the coming year given the weak global environment and rising costs.")
    out = tone.split_sentences(text)
    assert len(out) == 2 and out[0].startswith("Revenue grew") and out[1].startswith("We remain cautious")


def test_trend_up_flat_down_and_missing_data(tmp_path):
    p = tmp_path / "ml.csv"; make_csv(p)
    up, flat, down, two = (trend.trend_from_dataset(t, p) for t in ("UPCO", "FLATCO", "DOWNCO", "TWOCO"))
    assert up["score"] > 0.7 and abs(flat["score"]) < 0.01 and down["score"] < -0.7
    assert up["years"] == ["2023", "2024", "2025"]                           # the December row was ignored
    assert two["signals_used"] == 3                                          # growth has one value, margin and ROE have changes
    assert trend.trend_from_dataset("NOPE", p) is None
    assert trend.trend_from_dataset("UPCO.NS", p)["score"] == up["score"]    # .NS suffix accepted


def test_tone_and_sentence_selection(tmp_path):
    pages = [(1, "Revenue grew strongly during the year because demand was strong across every one of our segments. " * 3),
             (2, "Profit fell sharply as costs rose and the overall environment stayed weak for most of the year. " * 3),
             (3, "The board met seven times and reviewed the related party transactions of the company this year. " * 3)]
    store.build_index("XCO", ingest.build_chunks(pages, min_chars=50), HashEmbedder(), store=str(tmp_path))
    rag = RagService(embedder=HashEmbedder(), llm=StubLLM("x"), store_dir=str(tmp_path))
    sents = tone.select_sentences(rag, "XCO", k=5)
    assert {s["page"] for s in sents} == {1, 2, 3} and len({s["text"] for s in sents}) == len(sents)   # no duplicates
    assert sents == sorted(sents, key=lambda d: (d["page"], d["text"]))
    sc = StubScorer().score([s["text"] for s in sents])
    t = tone.tone_of(sc)
    assert -1 <= t <= 1 and tone.tone_of([]) is None
    a = service.analyse_company("XCO", rag, StubScorer(), _csv(tmp_path))
    assert a["sentences"] == len(sents) and a["most_positive"][0]["page"] == 1 and a["most_negative"][0]["page"] == 2
    assert 0 < a["positive_share"] < 1 and a["trend"] is None            # XCO has no yearly data


def _csv(tmp_path):
    p = tmp_path / "ml2.csv"; make_csv(p); return str(p)


def test_verdicts_compare_across_companies():
    mk = lambda t, tone_, tr: {"ticker": t, "tone": tone_, "trend": {"score": tr}}
    cs = [mk("A", 0.30, -0.6), mk("B", 0.10, 0.5), mk("C", 0.12, 0.6), mk("D", 0.11, 0.55), mk("E", 0.10, 0.52), {"ticker": "F", "tone": None, "trend": None}]
    service.add_verdicts(cs)
    by = {c["ticker"]: c for c in cs}
    assert by["A"]["verdict"] == "says_more_than_shows" and by["A"]["gap"] > 1       # upbeat words, falling numbers
    assert by["F"]["verdict"] == "not_enough_data"
    mk2 = [mk("A", -0.20, 0.8), mk("B", 0.10, 0.1), mk("C", 0.12, 0.12), mk("D", 0.11, 0.11)]
    service.add_verdicts(mk2)
    assert mk2[0]["verdict"] == "shows_more_than_says"                                # gloomy words, strong numbers
    two = [mk("A", 0.1, 0.1), mk("B", 0.2, 0.2)]
    service.add_verdicts(two); assert two[0]["verdict"] == "not_enough_companies"
    same = [mk("A", 0.1, 0.1), mk("B", 0.1, 0.1), mk("C", 0.1, 0.1)]
    service.add_verdicts(same); assert all(c["verdict"] == "consistent" for c in same)   # no spread, no flag


def test_cache_and_api(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "DEFAULT_CACHE", str(tmp_path / "detector.json"))
    app = FastAPI(); app.include_router(det_router.router, prefix="/detector")
    c = TestClient(app)
    r = c.get("/detector/summary")                                      # nothing saved yet
    assert r.status_code == 404 and "run_detector.py" in r.json()["detail"]
    service.save([{"ticker": "TCS", "tone": 0.1, "verdict": "consistent"}], model="m")
    assert c.get("/detector/summary").json()["companies"][0]["ticker"] == "TCS"
    assert c.get("/detector/TCS.NS").json()["verdict"] == "consistent"
    assert c.get("/detector/HUL").status_code == 404                    # alias works, but there is no result for HINDUNILVR
