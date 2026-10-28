"""The answer writer: Google Gemini or Groq.
Settings come from the environment or from a .env file next to main.py:
    LLM_PROVIDER=groq            (or gemini; if left out, Groq is used when only a Groq key is set)
    GEMINI_API_KEY / GEMINI_MODEL, GROQ_API_KEY / GROQ_MODEL"""
import os
import re
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:                                   # python-dotenv is optional
    pass


DEFAULT_MODEL = "gemini-3.8-flash"          # if Google retires it, the code finds a current Flash model by itself


def pick_flash_model(client):
    """Ask Gemini which models this key can use and return the newest stable plain Flash model, or None.
    Lite, image, audio and live variants are skipped."""
    names = []
    for m in client.models.list():
        actions = list(getattr(m, "supported_actions", None) or [])
        if actions and "generateContent" not in actions:
            continue
        names.append((getattr(m, "name", "") or "").replace("models/", ""))
    flash = [n for n in names if re.fullmatch(r"gemini-\d+(?:\.\d+)?-flash(?:-preview)?", n)]
    if not flash:
        return None
    version = lambda n: tuple(int(x) for x in re.findall(r"\d+", n.split("-flash")[0]))
    stable = [n for n in flash if not n.endswith("-preview")]       # prefer a stable model; use a preview only if nothing else exists
    return max(stable or flash, key=version)


class LLMError(Exception):
    """A problem with the language model that the user can understand and fix."""


class GeminiLLM:
    def __init__(self, model=None, api_key=None):
        self.model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.name = self.model
        self.timeout = float(os.environ.get("GEMINI_TIMEOUT_SECONDS", "60"))     # seconds to wait before giving up

    def _call(self, client, model, prompt):
        from google.genai import types
        resp = client.models.generate_content(model=model, contents=prompt,
                                              config=types.GenerateContentConfig(temperature=0.1))
        return (resp.text or "").strip()

    def generate(self, prompt):
        if not self.api_key:
            raise LLMError("GEMINI_API_KEY is not set. Put it in the .env file next to main.py and restart the backend.")
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=int(self.timeout * 1000)))
            try:
                text = self._call(client, self.model, prompt)
            except Exception as e:
                low = str(e).lower()
                if not ("404" in str(e) or "not found" in low or "no longer available" in low):
                    raise
                try:
                    found = pick_flash_model(client)             # the model name is out of date: look for a current one
                except Exception:
                    found = None                                 # listing failed too: report the original problem
                if not found or found == self.model:
                    raise
                self.model = self.name = found
                text = self._call(client, found, prompt)
        except Exception as e:                        # network, quota, wrong model name, bad key ...
            msg = str(e)
            low = msg.lower()
            if "timed out" in low or "timeout" in low or "deadline" in low:
                raise LLMError(f"Gemini did not answer within {self.timeout:.0f} seconds. Check your internet connection "
                               "(a VPN, proxy or firewall can block it) and try again.") from e
            if "429" in msg or "quota" in low or "resource_exhausted" in low:
                raise LLMError("Gemini's free quota is used up for now. Wait a minute and try again.") from e
            if "404" in msg or "not found" in low:
                raise LLMError(f"Gemini does not know the model '{self.model}' and no current Flash model could be found for your key. "
                               "Run: python scripts/list_gemini_models.py, then set GEMINI_MODEL in .env.") from e
            if "503" in msg or "overloaded" in low or "unavailable" in low:
                raise LLMError("Gemini is busy right now. Wait a minute and try again.") from e
            if "api key" in low or "403" in msg or "401" in msg:
                raise LLMError("Gemini rejected the API key. Check GEMINI_API_KEY in .env.") from e
            raise LLMError("The Gemini request failed: " + msg[:200]) from e
        if not text:
            raise LLMError("Gemini returned an empty answer. Try rephrasing the question.")
        return text


GROQ_URL = "https://api.groq.com/openai/v1"
GROQ_DEFAULT = "openai/gpt-oss-120b"
GROQ_PREFERRED = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.1-8b-instant"]


def _post(url, headers, payload, timeout):
    import httpx
    return httpx.post(url, headers=headers, json=payload, timeout=timeout)


def _get(url, headers, timeout):
    import httpx
    return httpx.get(url, headers=headers, timeout=timeout)


def pick_groq_model(ids):
    """Choose a chat model from the ids Groq lists for this key. Safety, speech and embedding models are skipped."""
    ids = list(ids)
    for m in GROQ_PREFERRED:
        if m in ids:
            return m
    chat = sorted(i for i in ids if re.search(r"llama|gpt-oss|qwen|kimi|gemma", i) and not re.search(r"guard|whisper|tts|safeguard|embed", i))
    return chat[0] if chat else None


class GroqLLM:
    """Groq's OpenAI-style chat API. Fast, with a free tier. Key from console.groq.com/keys."""

    def __init__(self, model=None, api_key=None):
        self.model = model or os.environ.get("GROQ_MODEL", GROQ_DEFAULT)
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.name = self.model
        self.timeout = float(os.environ.get("GROQ_TIMEOUT_SECONDS", "60"))
        self.retries = int(os.environ.get("GROQ_RETRIES", "3"))                 # waits and tries again when the free rate limit is hit

    @staticmethod
    def _retry_wait(r):
        """Seconds Groq says to wait after a 429 (Retry-After header or 'try again in 6.3s'); None if unknown or over a minute."""
        wait = None
        try:
            wait = float(r.headers.get("retry-after"))
        except Exception:
            m = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", getattr(r, "text", "") or "", re.I)
            if m:
                wait = int(m.group(1) or 0) * 60 + float(m.group(2))
        return wait + 1 if wait is not None and wait <= 60 else None

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "User-Agent": "FinSightAI/1.0"}

    def list_models(self):
        r = _get(f"{GROQ_URL}/models", self._headers(), self.timeout)
        if r.status_code != 200:
            raise LLMError(self._problem(r))
        return [m["id"] for m in r.json().get("data", [])]

    def _problem(self, r):
        try:
            detail = (r.json().get("error") or {}).get("message", "")
        except Exception:
            detail = ""
        if r.status_code in (401, 403):
            return "Groq rejected the API key. Check GROQ_API_KEY in .env (it starts with gsk_)."
        if r.status_code == 429:
            return "Groq's free rate limit was reached. Wait a minute and try again."
        if r.status_code >= 500:
            return "Groq is busy right now. Wait a minute and try again."
        return f"Groq returned an error ({r.status_code}): {detail[:200]}"

    def _chat(self, model, prompt):
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 1500}
        if "gpt-oss" in model:
            payload["reasoning_effort"] = "low"                      # these models think first; keep that short
        return _post(f"{GROQ_URL}/chat/completions", self._headers(), payload, self.timeout)

    def generate(self, prompt):
        if not self.api_key:
            raise LLMError("GROQ_API_KEY is not set. Put it in the .env file next to main.py and restart the backend.")
        try:
            r = self._chat(self.model, prompt)
            for _ in range(self.retries):
                wait = self._retry_wait(r) if r.status_code == 429 else None
                if wait is None:
                    break
                time.sleep(wait)
                r = self._chat(self.model, prompt)
            gone = r.status_code in (400, 404) and re.search(r"model_not_found|does not exist|decommission|not found", r.text, re.I)
            if gone:                                                   # the model name is out of date: look for a current one
                try:
                    found = pick_groq_model(self.list_models())
                except Exception:
                    found = None
                if found and found != self.model:
                    self.model = self.name = found
                    r = self._chat(found, prompt)
        except LLMError:
            raise
        except Exception as e:
            low = (type(e).__name__ + " " + str(e)).lower()
            if "timeout" in low or "timed out" in low:
                raise LLMError(f"Groq did not answer within {self.timeout:.0f} seconds. Check your internet connection "
                               "(a VPN, proxy or firewall can block it) and try again.") from e
            raise LLMError("The Groq request failed: " + str(e)[:200]) from e
        if r.status_code != 200:
            raise LLMError(self._problem(r))
        try:
            text = (r.json()["choices"][0]["message"]["content"] or "").strip()
        except Exception:
            text = ""
        if not text:
            raise LLMError("Groq returned an empty answer. Try rephrasing the question.")
        return text


def make_llm():
    """Pick the answer writer from the settings. LLM_PROVIDER=groq or gemini; otherwise Groq only if that is the only key set."""
    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if not provider:
        has_gemini = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
        provider = "groq" if os.environ.get("GROQ_API_KEY") and not has_gemini else "gemini"
    return GroqLLM() if provider == "groq" else GeminiLLM()
