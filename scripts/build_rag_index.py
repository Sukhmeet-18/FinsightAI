"""Build the search index for each company's annual report (run once, or again when a PDF changes).

Run from the project folder (the one with main.py):
    python scripts/build_rag_index.py                 # every documents/<COMPANY>/<any>.pdf
    python scripts/build_rag_index.py --only TCS ITC  # just these companies
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.getcwd())

from backend.rag import store                       # noqa: E402
from backend.rag.embedder import SentenceEmbedder   # noqa: E402
from backend.rag.ingest import build_chunks, extract_pages, find_report_pdfs, normalise_ticker, odd_symbol_rate   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="tickers to build, for example: TCS ITC")
    ap.add_argument("--docs", default="documents", help="folder holding one sub-folder per company, each with its PDF")
    args = ap.parse_args()

    found = find_report_pdfs(args.docs)                      # {ticker: pdf}; any PDF file name works
    wanted = {normalise_ticker(t) for t in args.only} if args.only else None
    jobs = [(t, p) for t, p in found.items() if wanted is None or t in wanted]
    if not jobs:
        print(f"No PDFs found. Put one PDF in each folder, for example {args.docs}\\TCS\\report.pdf")
        return
    for folder in sorted(os.listdir(args.docs)):
        if normalise_ticker(folder) not in found:
            print(f"Note: no PDF in {os.path.join(args.docs, folder)}, skipping it.")

    print("Loading the embedding model (the first time this downloads about 130 MB)...")
    embedder = SentenceEmbedder()
    for ticker, pdf in jobs:
        t0 = time.time()
        print(f"\n{ticker}: reading {pdf}")
        pages = extract_pages(pdf)
        readable = sum(1 for _, text in pages if len(text) >= 200)
        print(f"  {len(pages)} pages, {readable} with readable text")
        if readable < 0.5 * len(pages):
            print("  WARNING: under half the pages have text. This looks like a scanned PDF; answers will be poor.")
        rate = odd_symbol_rate(pages)
        if rate > 1.0:
            print(f"  WARNING: {rate:.1f} odd symbols per 1,000 characters. The PDF's fonts are badly encoded, so some numbers may be wrong. "
                  "Try the original (not compressed) PDF from the company's site.")
        chunks = build_chunks(pages)
        if not chunks:
            print("  No readable text found, skipping.")
            continue
        print(f"  {len(chunks)} passages; embedding them (a few minutes for a long report)...")
        n = store.build_index(ticker, chunks, embedder,
                              meta={"pdf": pdf, "pages": len(pages), "pages_with_text": readable})
        print(f"  done: {n} passages indexed in {time.time() - t0:.0f} s")
    print("\nIndexes built. Companies ready:", ", ".join(store.available()))


if __name__ == "__main__":
    main()
