"""Run the Say vs. Show analysis for every company that has a search index, and save the results.

Needs the indexes from build_rag_index.py. The first run downloads FinBERT (about 440 MB) and takes a few minutes.

Run from the project folder:
    python scripts/run_detector.py
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.getcwd())

from backend.detector import service                  # noqa: E402
from backend.rag import store                         # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join("data", "ml_dataset.csv"), help="yearly growth, margin and ROE")
    args = ap.parse_args()
    tickers = store.available()
    if not tickers:
        print("No search indexes yet. Run: python scripts/build_rag_index.py")
        return
    from backend.detector.tone import FinBertScorer
    from backend.rag.service import RagService
    print("Loading the embedding model and FinBERT (the first time this downloads about 570 MB in total)...")
    rag, scorer = RagService(), FinBertScorer()
    companies = []
    for t in tickers:
        t0 = time.time()
        c = service.analyse_company(t, rag, scorer, args.data)
        companies.append(c)
        tr = (c["trend"] or {}).get("score")
        print(f"{t:11s} {c['sentences']:4d} sentences | tone {c['tone']:+.3f} | trend {tr if tr is None else format(tr, '+.3f')} | {time.time() - t0:.0f} s")
    service.add_verdicts(companies)
    service.save(companies, model=scorer.name)
    print("\nVerdicts (relative to the other companies):")
    for c in companies:
        print(f"  {c['ticker']:11s} gap {c.get('gap', 'n/a')} -> {c['verdict']}")
    print("\nSaved to", service.DEFAULT_CACHE)


if __name__ == "__main__":
    main()
