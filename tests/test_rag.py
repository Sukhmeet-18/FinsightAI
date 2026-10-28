import os
import re
import sys
import zlib

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

sys.path.insert(0, os.getcwd())
from backend.rag import ingest, router as rag_router, store                  # noqa: E402
from backend.rag.llm import GeminiLLM, LLMError                              # noqa: E402
from backend.rag.service import NOT_FOUND, RagService                        # noqa: E402

DIM = 256


class HashEmbedder:
    """Stand-in for the real model: hashes words into a fixed-size unit vector (same words, similar vectors)."""
    name = "hash-test"

    def encode(self, texts, batch_size=32):
        out = np.zeros((len(texts), DIM), dtype="float32")
        for i, t in enumerate(texts):
            for w in re.findall(r"[a-z0-9]+", t.lower()):
                out[i, zlib.crc32(w.encode()) % DIM] += 1.0
        n = np.linalg.norm(out, axis=1, keepdims=True)
        n[n == 0] = 1
        return out / n


class StubLLM:
    name = "stub"

    def __init__(self, reply):
        self.reply, self.prompts = reply, []

    def generate(self, prompt):
        self.prompts.append(prompt)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


PAGES = {
    2: "Revenue from operations grew to Rs 5,00,000 crore in fiscal 2025 driven by retail and digital services. " * 6,
    3: "Principal risks include cyber attacks on our systems, currency swings and changes in regulation. " * 6,
    4: "Total borrowings stood at Rs 90,000 crore at year end and net debt reduced during the year. " * 6,
    5: "The board of directors met seven times and the audit committee reviewed related party transactions. " * 6,
    7: "Sustainability report: emissions fell and the company planted trees across several villages. " * 6,
}


@pytest.fixture(scope="module")
def pdf_path(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("docs") / "annual_report.pdf")
    c = canvas.Canvas(path, pagesize=A4)
    for n in range(1, 9):                                   # 8 pages; pages 1, 6, 8 are cover or blank
        text = PAGES.get(n)
        if text:
            y = 800
            for line in re.findall(r".{1,90}(?:\s|$)", text):
                c.drawString(40, y, line.strip())
                y -= 14
        elif n == 1:
            c.drawString(40, 800, "Annual Report 2025")
        c.showPage()
    c.save()
    return path


@pytest.fixture()
def built(pdf_path, tmp_path):
    chunks = ingest.build_chunks(ingest.extract_pages(pdf_path))
    store.build_index("TCS", chunks, HashEmbedder(), store=str(tmp_path), meta={"pages": 8})
    return str(tmp_path), chunks


def test_pages_and_skipping(pdf_path):
    pages = ingest.extract_pages(pdf_path)
    assert [p for p, _ in pages] == list(range(1, 9))                       # 1-based PDF page numbers
    chunks = ingest.build_chunks(pages)
    assert {c["page"] for c in chunks} == {2, 3, 4, 5, 7}                  # cover and blank pages dropped
    assert any("Revenue from operations" in c["text"] for c in chunks if c["page"] == 2)


def test_chunking_rules():
    text = " ".join(f"word{i}" for i in range(1000))                        # about 6,900 characters
    parts = ingest.chunk_page(text)
    assert len(parts) > 5 and all(len(p) <= ingest.CHUNK_CHARS + 5 for p in parts)
    assert set(text.split()) <= set(" ".join(parts).split())                # nothing lost
    assert set(parts[0].split()[-3:]) & set(parts[1].split()[:30])          # neighbours overlap
    assert ingest.chunk_page("short") == ["short"]
    assert ingest.clean("a-\nb  c\x00d\n\n e") == "ab c d e"


def test_retrieval_finds_the_right_page(built):
    folder, _ = built
    svc = RagService(embedder=HashEmbedder(), llm=StubLLM("x"), store_dir=folder)
    for q, page in [("what was the revenue from operations", 2), ("main risks cyber attacks", 3),
                    ("total borrowings and net debt", 4)]:
        hits = svc.retrieve("TCS", q, k=3)
        assert hits[0]["page"] == page, (q, [h["page"] for h in hits])


def test_answer_with_citations_and_unverified_pages(built):
    folder, _ = built
    llm = StubLLM("Revenue grew to Rs 5,00,000 crore [p. 2]. A claim with a page we never showed [p. 99].")
    r = RagService(embedder=HashEmbedder(), llm=llm, store_dir=folder).ask("tcs", "What was the revenue?")
    assert r["found"] is True and r["ticker"] == "TCS"
    assert r["unverified_pages"] == [99]
    assert r["sources"][0]["page"] == 2 and r["sources"][0]["cited"] is True      # cited sources come first
    assert len({s["page"] for s in r["sources"]}) == len(r["sources"])            # one source per page
    p = llm.prompts[0]
    assert "[p. 2]" in p and "What was the revenue?" in p and "ONLY the excerpts" in p
    pages_in_prompt = [int(x) for x in re.findall(r"\[p\. (\d+)\]", p.split("Excerpts:")[1])]
    assert pages_in_prompt == sorted(pages_in_prompt)                              # excerpts in page order


def test_not_found_and_errors(built, tmp_path):
    folder, _ = built
    svc = RagService(embedder=HashEmbedder(), llm=StubLLM(NOT_FOUND), store_dir=folder)
    assert svc.ask("TCS", "Who won the cricket match?")["found"] is False
    with pytest.raises(ValueError):
        svc.ask("TCS", "   ")
    with pytest.raises(FileNotFoundError, match="has not been indexed"):
        svc.ask("ITC", "revenue?")


def test_gemini_wrapper_messages(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    llm = GeminiLLM()
    llm.api_key = None
    with pytest.raises(LLMError, match="GEMINI_API_KEY is not set"):
        llm.generate("hi")
    assert GeminiLLM(model="m").name == "m"


class _Resp:
    def __init__(self, text):
        self.text = text


def _fake_client(monkeypatch, behaviour):
    """Replace google.genai.Client so no network is used; `behaviour` returns a reply or raises."""
    from google import genai

    class Client:
        def __init__(self, api_key=None, http_options=None):
            assert api_key == "k" and http_options.timeout == 60000
            self.models = self

        def generate_content(self, model, contents, config):
            assert model == "m" and "hello" in contents and config.temperature == 0.1
            return behaviour()

    monkeypatch.setattr(genai, "Client", Client)


@pytest.mark.parametrize("raised,expect", [
    (Exception("429 RESOURCE_EXHAUSTED quota"), "free quota"),
    (Exception("404 models/x is not found"), "GEMINI_MODEL"),
    (Exception("403 API key not valid"), "rejected the API key"),
    (Exception("socket closed"), "request failed"),
])
def test_gemini_error_messages(monkeypatch, raised, expect):
    def boom():
        raise raised
    _fake_client(monkeypatch, boom)
    with pytest.raises(LLMError, match=expect):
        GeminiLLM(model="m", api_key="k").generate("hello")


def test_gemini_success_and_empty(monkeypatch):
    _fake_client(monkeypatch, lambda: _Resp("  Fine [p. 2].  "))
    assert GeminiLLM(model="m", api_key="k").generate("hello") == "Fine [p. 2]."
    _fake_client(monkeypatch, lambda: _Resp(None))
    with pytest.raises(LLMError, match="empty answer"):
        GeminiLLM(model="m", api_key="k").generate("hello")


def test_api(built, monkeypatch):
    folder, _ = built
    app = FastAPI()
    app.include_router(rag_router.router, prefix="/rag")
    c = TestClient(app)

    def use(reply):
        monkeypatch.setattr(rag_router, "get_service", lambda: RagService(embedder=HashEmbedder(), llm=StubLLM(reply), store_dir=folder))

    monkeypatch.setattr(store, "STORE_DIR", folder)
    listing = c.get("/rag/companies").json()
    assert listing == [{"ticker": "TCS", "chunks": len(built[1]), "pages": 8, "embedder": "hash-test"}]
    use("Debt was Rs 90,000 crore [p. 4].")
    r = c.post("/rag/ask", json={"ticker": "TCS.NS", "question": "total borrowings"})
    assert r.status_code == 200 and r.json()["sources"][0]["page"] == 4            # ".NS" is stripped
    assert c.post("/rag/ask", json={"ticker": "TCS", "question": " "}).status_code == 400
    assert c.post("/rag/ask", json={"ticker": "ITC", "question": "revenue"}).status_code == 404
    use(LLMError("Gemini's free quota is used up for now."))
    r = c.post("/rag/ask", json={"ticker": "TCS", "question": "revenue"})
    assert r.status_code == 503 and "quota" in r.json()["detail"]
    assert c.post("/rag/ask", json={"ticker": "TCS"}).status_code == 422


def test_missing_package_gives_a_readable_503(built, monkeypatch):
    folder, _ = built
    app = FastAPI()
    app.include_router(rag_router.router, prefix="/rag")

    class Broken:
        def ask(self, ticker, question):
            raise ImportError("No module named 'sentence_transformers'")

    monkeypatch.setattr(rag_router, "get_service", lambda: Broken())
    r = TestClient(app).post("/rag/ask", json={"ticker": "TCS", "question": "revenue"})
    assert r.status_code == 503 and "pip install -r requirements-rag.txt" in r.json()["detail"]


def test_running_headers_are_stripped_but_content_is_kept():
    word = lambda n: "".join(chr(97 + (n * k) % 26) for k in range(1, 9))       # a different word on every page
    pages = [f"ITC REPORT AND ACCOUNTS 2025 {n}\nRevenue story {word(n)} about growth.\nMore text {word(n + 50)}.\nPage {n}" for n in range(1, 31)]
    out = ingest.strip_running_lines(pages)
    assert all("REPORT AND ACCOUNTS" not in p for p in out)                   # header gone on every page
    assert all(f"Revenue story {word(n)}" in p for n, p in enumerate(out, start=1))   # real text survives
    short = pages[:5]
    assert ingest.strip_running_lines(short) == short                          # short documents are left alone
    middle = [f"Header\nline a\nline b\nline c\nUnique middle sentence {n}\nline d\nline e\nline f\nFooter" for n in range(30)]
    assert all("Unique middle sentence" in p for p in ingest.strip_running_lines(middle))   # only the edges are touched


def test_aliases_and_finding_report_pdfs(tmp_path):
    import shutil
    assert ingest.normalise_ticker("hul") == "HINDUNILVR" and ingest.normalise_ticker("TCS.NS") == "TCS"
    assert ingest.normalise_ticker("Maruti Suzuki") == "MARUTI"
    (tmp_path / "HUL").mkdir(); (tmp_path / "MARUTI").mkdir(); (tmp_path / "TCS").mkdir(); (tmp_path / "ITC").mkdir()
    sample = tmp_path / "x.pdf"
    c = canvas.Canvas(str(sample), pagesize=A4); c.drawString(40, 800, "hello"); c.showPage(); c.save()
    shutil.copy(sample, tmp_path / "HUL" / "annual_report.pdf")
    shutil.copy(sample, tmp_path / "MARUTI" / "MSIL_IR_2025-26_HR_updated_1.pdf")      # any file name works
    (tmp_path / "ITC" / "notes.txt").write_text("not a pdf")                          # ignored
    found = ingest.find_report_pdfs(str(tmp_path))
    assert sorted(found) == ["HINDUNILVR", "MARUTI"]                                  # HUL mapped, empty TCS and ITC skipped
    assert found["MARUTI"].endswith("MSIL_IR_2025-26_HR_updated_1.pdf")
    assert ingest.find_report_pdfs(str(tmp_path / "missing")) == {}


def test_router_accepts_the_hul_alias(built, monkeypatch):
    folder, _ = built
    app = FastAPI()
    app.include_router(rag_router.router, prefix="/rag")
    seen = {}

    class Spy:
        def ask(self, ticker, question):
            seen["t"] = ticker
            return {"ticker": ticker, "answer": "ok", "found": True, "sources": [], "unverified_pages": [], "model": "x", "question": question}

    monkeypatch.setattr(rag_router, "get_service", lambda: Spy())
    assert TestClient(app).post("/rag/ask", json={"ticker": "HUL", "question": "q"}).status_code == 200
    assert seen["t"] == "HINDUNILVR"


def test_badly_encoded_digits_are_repaired():
    bad = "Dividend payout was \u0f24\u03f0\u03f1,\u03f1\u03f4\u03f4 crore, final \u0f243\u03ec per share and \u0f2412\u03f2 in total (\u035eAGM\u035f)."
    assert ingest.clean(bad) == "Dividend payout was \u20b945,588 crore, final \u20b930 per share and \u20b9126 in total (\u201cAGM\u201d)."
    assert ingest.clean("Plain text with \u03b1 and \u03b2 stays: 2,40,893") == "Plain text with \u03b1 and \u03b2 stays: 2,40,893"   # real Greek letters are left alone
    assert ingest.odd_symbol_rate([(1, "clean text only")]) == 0
    assert ingest.odd_symbol_rate([(1, "ab\u0358cd")]) > 100


class _Model:
    def __init__(self, name, actions=("generateContent",)):
        self.name, self.supported_actions = name, list(actions)


def _client_with_models(monkeypatch, known, listed):
    """Fake Gemini: only models in `known` answer; `listed` is what models.list() returns."""
    from google import genai
    calls = []

    class Client:
        def __init__(self, api_key=None, http_options=None):
            self.models = self

        def generate_content(self, model, contents, config):
            calls.append(model)
            if model not in known:
                raise Exception(f"404 NOT_FOUND: models/{model} is not found for API version v1beta")
            return _Resp("Answer from " + model)

        def list(self):
            return iter(listed)

    monkeypatch.setattr(genai, "Client", Client)
    return calls


def test_old_model_name_falls_back_to_the_newest_flash_model(monkeypatch):
    from backend.rag.llm import pick_flash_model
    listed = [_Model("models/gemini-2.5-flash"), _Model("models/gemini-3.6-flash"), _Model("models/gemini-3.8-flash"),
              _Model("models/gemini-3.8-flash-lite"), _Model("models/gemini-3-pro-image"), _Model("models/gemini-3.1-flash-tts-preview"),
              _Model("models/gemini-3.9-flash-preview"), _Model("models/gemini-embedding-001", ["embedContent"]), _Model("models/gemma-4-31b-it")]
    class C:                                                                            # newest plain Flash wins; lite, image, tts and embeddings are skipped
        class models:
            list = staticmethod(lambda: iter(listed))
    assert pick_flash_model(C) == "gemini-3.8-flash"                                  # a stable model beats a newer preview
    C.models.list = staticmethod(lambda: iter([_Model("models/gemini-3.9-flash-preview"), _Model("models/gemini-3.6-flash-preview")]))
    assert pick_flash_model(C) == "gemini-3.9-flash-preview"                          # only previews exist: take the newest
    C.models.list = staticmethod(lambda: iter([_Model("models/gemini-3.8-flash-lite")]))
    assert pick_flash_model(C) is None


def test_fallback_is_remembered_and_stops_when_nothing_works(monkeypatch):
    listed = [_Model("models/gemini-3.8-flash")]
    calls = _client_with_models(monkeypatch, known={"gemini-3.8-flash"}, listed=listed)
    llm = GeminiLLM(model="gemini-2.5-flash", api_key="k")
    assert llm.generate("hello") == "Answer from gemini-3.8-flash"
    assert llm.model == llm.name == "gemini-3.8-flash"                                  # remembered for next time
    n = len(calls)
    llm.generate("again")
    assert calls[n:] == ["gemini-3.8-flash"]                                            # no second search
    _client_with_models(monkeypatch, known=set(), listed=[_Model("models/gemini-3.8-flash-lite")])
    with pytest.raises(LLMError, match="list_gemini_models.py"):
        GeminiLLM(model="gemini-2.5-flash", api_key="k").generate("hello")


@pytest.mark.parametrize("raised,expect", [
    (Exception("The read operation timed out"), "did not answer within 60 seconds"),
    (Exception("503 UNAVAILABLE: model is overloaded"), "busy right now"),
])
def test_slow_or_busy_gemini_gives_a_clear_message(monkeypatch, raised, expect):
    def boom():
        raise raised
    _fake_client(monkeypatch, boom)
    with pytest.raises(LLMError, match=expect):
        GeminiLLM(model="m", api_key="k").generate("hello")


# ---------------- Groq ----------------
class _HttpResp:
    def __init__(self, status=200, body=None, text=""):
        self.status_code, self._body = status, body if body is not None else {}
        self.text = text or str(self._body)

    def json(self):
        return self._body


def _chat_ok(text):
    return _HttpResp(200, {"choices": [{"message": {"content": text}}]})


def test_groq_request_and_answer(monkeypatch):
    from backend.rag import llm as L
    seen = []
    monkeypatch.setattr(L, "_post", lambda url, headers, payload, timeout: (seen.append((url, headers, payload, timeout)), _chat_ok("  Revenue was X [p. 4].  "))[1])
    g = L.GroqLLM(model="openai/gpt-oss-120b", api_key="gsk_test")
    assert g.generate("hello") == "Revenue was X [p. 4]."
    url, headers, payload, timeout = seen[0]
    assert url == "https://api.groq.com/openai/v1/chat/completions" and headers["Authorization"] == "Bearer gsk_test"
    assert payload["messages"] == [{"role": "user", "content": "hello"}] and payload["temperature"] == 0.1
    assert payload["reasoning_effort"] == "low" and timeout == 60                      # gpt-oss thinks first, so keep it short
    L.GroqLLM(model="llama-3.3-70b-versatile", api_key="k").generate("hi")
    assert "reasoning_effort" not in seen[1][2]                                      # other models do not accept it


def test_groq_old_model_falls_back_and_is_remembered(monkeypatch):
    from backend.rag import llm as L
    calls = []

    def post(url, headers, payload, timeout):
        calls.append(payload["model"])
        if payload["model"] != "openai/gpt-oss-20b":
            return _HttpResp(404, {"error": {"message": "The model `x` does not exist", "code": "model_not_found"}})
        return _chat_ok("fine")
    monkeypatch.setattr(L, "_post", post)
    monkeypatch.setattr(L, "_get", lambda url, headers, timeout: _HttpResp(200, {"data": [{"id": "whisper-large-v3"}, {"id": "meta-llama/llama-guard-4-12b"}, {"id": "openai/gpt-oss-20b"}]}))
    g = L.GroqLLM(model="old-model", api_key="k")
    assert g.generate("q") == "fine" and g.model == g.name == "openai/gpt-oss-20b"
    n = len(calls); g.generate("again"); assert calls[n:] == ["openai/gpt-oss-20b"]           # no second search


@pytest.mark.parametrize("resp,expect", [
    (_HttpResp(401, {"error": {"message": "Invalid API Key"}}), "rejected the API key"),
    (_HttpResp(429, {"error": {"message": "rate limit"}}), "rate limit was reached"),
    (_HttpResp(503, {}), "busy right now"),
    (_HttpResp(400, {"error": {"message": "context too long"}}), "context too long"),
    (_chat_ok(""), "empty answer"),
    (_HttpResp(200, {"unexpected": True}), "empty answer"),
])
def test_groq_error_messages(monkeypatch, resp, expect):
    from backend.rag import llm as L
    monkeypatch.setattr(L, "_post", lambda *a, **k: resp)
    with pytest.raises(LLMError, match=expect):
        L.GroqLLM(model="m", api_key="k").generate("q")


def test_groq_timeout_missing_key_and_dead_model_list(monkeypatch):
    import httpx
    from backend.rag import llm as L

    def slow(*a, **k):
        raise httpx.ReadTimeout("The read operation timed out")
    monkeypatch.setattr(L, "_post", slow)
    with pytest.raises(LLMError, match="did not answer within 60 seconds"):
        L.GroqLLM(model="m", api_key="k").generate("q")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(LLMError, match="GROQ_API_KEY is not set"):
        L.GroqLLM(api_key=None).generate("q")
    monkeypatch.setattr(L, "_post", lambda *a, **k: _HttpResp(404, {"error": {"code": "model_not_found", "message": "no"}}))
    monkeypatch.setattr(L, "_get", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("listing is down")))
    with pytest.raises(LLMError, match="Groq returned an error \\(404\\)"):                 # listing failed too: the original problem is reported
        L.GroqLLM(model="m", api_key="k").generate("q")


def test_pick_groq_model_and_provider_switch(monkeypatch):
    from backend.rag import llm as L
    assert L.pick_groq_model(["whisper-large-v3", "openai/gpt-oss-20b", "openai/gpt-oss-120b"]) == "openai/gpt-oss-120b"
    assert L.pick_groq_model(["x", "llama-3.3-70b-versatile", "openai/gpt-oss-120b"]) == "llama-3.3-70b-versatile"
    assert L.pick_groq_model(["meta-llama/llama-guard-4-12b", "whisper-large-v3", "playai-tts"]) is None
    assert L.pick_groq_model(["qwen/qwen3-32b", "meta-llama/llama-guard-4-12b"]) == "qwen/qwen3-32b"
    for k in ("LLM_PROVIDER", "GROQ_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert isinstance(L.make_llm(), L.GeminiLLM)                                              # nothing set: Gemini, as before
    monkeypatch.setenv("GROQ_API_KEY", "gsk_x")
    assert isinstance(L.make_llm(), L.GroqLLM)                                                # only a Groq key: Groq
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    assert isinstance(L.make_llm(), L.GeminiLLM)                                              # both keys: Gemini unless told otherwise
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    assert isinstance(L.make_llm(), L.GroqLLM)                                                # the switch wins
    monkeypatch.setenv("LLM_PROVIDER", "GEMINI")
    assert isinstance(L.make_llm(), L.GeminiLLM)
