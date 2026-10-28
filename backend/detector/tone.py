"""Score the tone of the narrative parts of an annual report with FinBERT, sentence by sentence."""
import random
import re

QUERIES = [
    "management discussion and analysis of the year's business performance",
    "outlook and growth opportunities for the coming year",
    "challenges, risks and headwinds faced by the business",
    "strategy, priorities and key achievements during the year",
]
MIN_WORDS, MAX_WORDS = 6, 60
# Legal and meeting boilerplate that says nothing about how the business is doing
BOILERPLATE = re.compile(r"hereby given|special resolution|ordinary resolution|\bDIN\b|pursuant to (?:section|regulation)|"
                         r"registered office|e-voting|proxy form|record date|book closure", re.I)


def split_sentences(text):
    """Cut text into sentences and keep only readable prose (not table rows or lists of numbers)."""
    out = []
    for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"“‘(])", text):
        s = s.strip()
        words = s.split()
        if not (MIN_WORDS <= len(words) <= MAX_WORDS):
            continue
        letters = sum(c.isalpha() for c in s)
        digits = sum(c.isdigit() for c in s)
        if letters < 0.6 * len(s) or digits > 0.15 * len(s) or BOILERPLATE.search(s):
            continue
        out.append(s)
    return out


def select_sentences(rag, ticker, queries=QUERIES, k=40, cap=500, seed=7):
    """Use the report's own search index to pull narrative passages, then split them into sentences.
    Returns [{"page": int, "text": str}]; at most `cap` sentences, sampled with a fixed seed."""
    seen, sents = set(), []
    for q in queries:
        for hit in rag.retrieve(ticker, q, k=k):
            for s in split_sentences(hit["text"]):
                key = s.lower()
                if key not in seen:
                    seen.add(key)
                    sents.append({"page": hit["page"], "text": s})
    if len(sents) > cap:
        sents = random.Random(seed).sample(sents, cap)
    return sorted(sents, key=lambda d: (d["page"], d["text"]))


class FinBertScorer:
    """FinBERT (ProsusAI/finbert): a BERT model trained on financial text. Downloaded the first time it is used."""
    name = "ProsusAI/finbert"

    def __init__(self):
        from transformers import pipeline                       # imported late: slow to load
        self.pipe = pipeline("text-classification", model=self.name, top_k=None, truncation=True, max_length=128)

    def score(self, sentences):
        """Return one {"pos", "neg", "neu"} dict of probabilities per sentence."""
        out = []
        for res in self.pipe(list(sentences), batch_size=16):
            d = {r["label"].lower(): float(r["score"]) for r in res}
            out.append({"pos": d.get("positive", 0.0), "neg": d.get("negative", 0.0), "neu": d.get("neutral", 0.0)})
        return out


def tone_of(scores):
    """Net tone in [-1, 1]: average positive probability minus average negative probability."""
    if not scores:
        return None
    return sum(s["pos"] - s["neg"] for s in scores) / len(scores)
