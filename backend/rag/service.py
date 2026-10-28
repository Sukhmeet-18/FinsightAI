"""Find the best passages in a company's annual report, then ask the language model to answer from them only."""
import re

from . import store
from .llm import make_llm

COMPANY_NAMES = {
    "RELIANCE": "Reliance Industries", "TCS": "Tata Consultancy Services",
    "HINDUNILVR": "Hindustan Unilever", "MARUTI": "Maruti Suzuki India", "ITC": "ITC Limited",
}
NOT_FOUND = "I could not find this in the report excerpts."

PROMPT = """You answer questions about {company}'s annual report using ONLY the excerpts below.

Rules:
- Use only facts that appear in the excerpts. If the answer is not there, reply exactly: """ + NOT_FOUND + """
- After each sentence that uses an excerpt, cite its page like [p. 42].
- Quote numbers exactly as written, with their units and year. Do not estimate or calculate beyond what the excerpts say.
- Be concise: at most 6 sentences, in plain words.

Excerpts:
{excerpts}

Question: {question}

Answer:"""


class RagService:
    def __init__(self, embedder=None, llm=None, store_dir=None, k=6):
        self._embedder = embedder
        self.llm = llm or make_llm()
        self.store_dir = store_dir
        self.k = k
        self._cache = {}

    @property
    def embedder(self):
        if self._embedder is None:
            from .embedder import SentenceEmbedder         # loads the model on the first question
            self._embedder = SentenceEmbedder()
        return self._embedder

    def _load(self, ticker):
        t = ticker.upper()
        if t not in self._cache:
            self._cache[t] = store.load_index(t, self.store_dir)
        return self._cache[t]

    def retrieve(self, ticker, question, k=None):
        index, data = self._load(ticker)
        qv = self.embedder.encode([question])[0]
        return store.search(index, data, qv, k or self.k)

    def ask(self, ticker, question):
        question = (question or "").strip()
        if not question:
            raise ValueError("Please type a question.")
        hits = self.retrieve(ticker, question)
        if not hits:
            raise FileNotFoundError(f"The {ticker.upper()} index is empty. Rebuild it with scripts/build_rag_index.py.")
        ordered = sorted(hits, key=lambda h: h["page"])                # page order reads more naturally
        excerpts = "\n\n".join(f"[p. {h['page']}] {h['text']}" for h in ordered)
        prompt = PROMPT.format(company=COMPANY_NAMES.get(ticker.upper(), ticker.upper()),
                               excerpts=excerpts, question=question)
        answer = self.llm.generate(prompt)

        cited = sorted({int(p) for p in re.findall(r"\[p\.\s*(\d+)\]", answer)})
        known = {h["page"] for h in hits}
        best = {}                                                       # one source per page: its best passage
        for h in hits:
            if h["page"] not in best or h["score"] > best[h["page"]]["score"]:
                best[h["page"]] = h
        sources = [{"page": p, "text": h["text"][:400], "score": round(h["score"], 3), "cited": p in cited}
                   for p, h in best.items()]
        sources.sort(key=lambda s: (not s["cited"], -s["score"]))
        return {
            "ticker": ticker.upper(), "question": question, "answer": answer,
            "found": not answer.strip().lower().startswith("i could not find"),
            "sources": sources,
            "unverified_pages": [p for p in cited if p not in known],   # pages the model cited that we never showed it
            "model": getattr(self.llm, "name", ""),
        }
