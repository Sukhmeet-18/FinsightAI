"""Ask a few sample questions and print the answers with their cited pages (needs the index and your Groq or Gemini key).
Every answer is also saved to reports/rag/rag_eval.csv, so you can mark each one right or wrong for the report.

Run from the project folder:
    python scripts/try_rag.py                 # every company that has an index
    python scripts/try_rag.py --ticker TCS --question "What was the revenue this year?"
    python scripts/try_rag.py --pause 8       # wait longer between questions if the free rate limit is hit
"""
import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.getcwd())

from backend.rag import store                       # noqa: E402
from backend.rag.llm import LLMError                # noqa: E402
from backend.rag.service import RagService          # noqa: E402

SAMPLES = ["What was the total revenue this year?",
           "What are the biggest risks the company mentions?",
           "How much debt does the company have?"]
OUT = os.path.join("reports", "rag", "rag_eval.csv")
FIELDS = ["ticker", "question", "answer", "pages_shown", "pages_cited", "not_among_retrieved", "correct (fill in)", "page correct (fill in)"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker")
    ap.add_argument("--question")
    ap.add_argument("--pause", type=float, default=4.0, help="seconds to wait between questions")
    args = ap.parse_args()
    tickers = [args.ticker.upper()] if args.ticker else store.available()
    if not tickers:
        print("No indexes built yet. Run: python scripts/build_rag_index.py")
        return
    svc = RagService()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    new_file = not os.path.exists(OUT)
    with open(OUT, "a", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        for t in tickers:
            for q in ([args.question] if args.question else SAMPLES):
                print(f"\n=== {t} | {q}")
                try:
                    r = svc.ask(t, q)
                except LLMError as e:
                    print("FAILED:", e)
                    continue
                shown = [s["page"] for s in r["sources"]]
                cited = [s["page"] for s in r["sources"] if s["cited"]]
                print(r["answer"])
                print("pages shown:", shown, "| cited:", cited, "| not among retrieved:", r["unverified_pages"])
                w.writerow({"ticker": t, "question": q, "answer": r["answer"], "pages_shown": shown, "pages_cited": cited,
                            "not_among_retrieved": r["unverified_pages"], "correct (fill in)": "", "page correct (fill in)": ""})
                fh.flush()
                time.sleep(args.pause)
    print(f"\nSaved to {OUT}")


if __name__ == "__main__":
    main()
