"""Read an annual-report PDF page by page and cut it into overlapping chunks that remember their page."""
import re

MIN_PAGE_CHARS = 200     # skip near-empty pages (covers, blank pages, pages that are only images)
CHUNK_CHARS = 1000
OVERLAP_CHARS = 150


# Some report PDFs (for example a compressed TCS file) store digits and symbols under the wrong character
# codes, so a reader returns Greek letters instead. The pattern is regular, so we can map them back.
_GLYPH_FIXES = {**{chr(0x03EC + d): str(d) for d in range(10)},       # U+03EC..U+03F5 are the digits 0 to 9
                "\u0f24": "\u20b9", "\u035e": "\u201c", "\u035f": "\u201d", "\u037b": "\u2022", "\u0357": ":"}
_GLYPH_TABLE = str.maketrans(_GLYPH_FIXES)
_ODD = re.compile(r"[\u0370-\u03FF\u0300-\u036F\u02B0-\u02FF\u0F00-\u0FFF]")


def odd_symbol_rate(pages):
    """Odd symbols per 1,000 characters that are still in the text after cleaning (0 for normal English reports)."""
    total = sum(len(t) for _, t in pages) or 1
    return 1000 * sum(len(_ODD.findall(t)) for _, t in pages) / total


def clean(text):
    text = text.translate(_GLYPH_TABLE)
    text = text.replace("\x00", " ")
    text = re.sub(r"-\n(?=[a-z])", "", text)         # join words hyphenated across a line break
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _norm_line(line):
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", line)).strip().lower()


def strip_running_lines(raw_pages, edge=3, share=0.25, min_pages=20):
    """Drop running headers and footers (for example 'REPORT AND ACCOUNTS 2025 ... ITC Limited').
    Only the first and last `edge` lines of each page are looked at, and a line is dropped when its
    shape (numbers ignored) shows up on at least `share` of the pages. Short documents are left alone."""
    if len(raw_pages) < min_pages:
        return raw_pages
    split = [[ln for ln in (t or "").split("\n") if ln.strip()] for t in raw_pages]
    counts = {}
    for lines in split:
        edges = set(_norm_line(ln) for ln in lines[:edge] + lines[-edge:])
        for e in edges:
            if 0 < len(e) <= 100:
                counts[e] = counts.get(e, 0) + 1
    limit = share * len(raw_pages)
    out = []
    for lines in split:
        keep = []
        for k, ln in enumerate(lines):
            at_edge = k < edge or k >= len(lines) - edge
            if at_edge and counts.get(_norm_line(ln), 0) >= limit and len(_norm_line(ln)) <= 100:
                continue
            keep.append(ln)
        out.append("\n".join(keep))
    return out


def extract_pages(pdf_path):
    """Return [(page_number, text)]. Page numbers are 1-based PDF pages: the number your PDF viewer shows."""
    from pypdf import PdfReader                      # imported here so the backend starts even before pypdf is installed
    reader = PdfReader(pdf_path)
    raw = []
    for page in reader.pages:
        try:
            raw.append(page.extract_text() or "")
        except Exception:                            # one damaged page should not stop the whole report
            raw.append("")
    raw = strip_running_lines(raw)
    return [(i, clean(t)) for i, t in enumerate(raw, start=1)]


def chunk_page(text, size=CHUNK_CHARS, overlap=OVERLAP_CHARS):
    """Split one page into pieces of about `size` characters, cut at a space, sharing `overlap` characters."""
    if len(text) <= size:
        return [text]
    out, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = text.rfind(" ", start + size // 2, end)
            if cut != -1:
                end = cut
        out.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return out


def build_chunks(pages, min_chars=MIN_PAGE_CHARS):
    """Every chunk stays inside one page, so a citation always points to exactly one PDF page."""
    chunks = []
    for page_no, text in pages:
        if len(text) < min_chars:
            continue
        for piece in chunk_page(text):
            chunks.append({"page": page_no, "text": piece})
    return chunks


# Folder names people use for a company, mapped to the ticker the app uses.
ALIASES = {"HUL": "HINDUNILVR", "HINDUSTANUNILEVER": "HINDUNILVR", "RIL": "RELIANCE", "MSIL": "MARUTI", "MARUTISUZUKI": "MARUTI"}


def normalise_ticker(name):
    t = (name or "").upper().replace(".NS", "").replace(" ", "").replace("_", "")
    return ALIASES.get(t, t)


def find_report_pdfs(docs_dir):
    """Look in documents/<NAME>/ and return {ticker: pdf_path}. Any PDF name works; if a folder holds
    several PDFs the largest one is used. Empty folders are skipped."""
    import os
    found = {}
    if not os.path.isdir(docs_dir):
        return found
    for name in sorted(os.listdir(docs_dir)):
        folder = os.path.join(docs_dir, name)
        if not os.path.isdir(folder):
            continue
        pdfs = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".pdf")]
        if pdfs:
            found[normalise_ticker(name)] = max(pdfs, key=os.path.getsize)
    return found
