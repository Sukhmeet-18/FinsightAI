"""Quick health check for the report assistant. It tells you which step is slow or broken.

Run from the project folder:
    python scripts/check_gemini.py
Nothing here prints your key.
"""
import os
import sys
import time

sys.path.insert(0, os.getcwd())

from backend.rag.llm import GeminiLLM, pick_flash_model     # noqa: E402  (also loads .env)


MAX_TRIES, TRY_SECONDS = 4, 25


def candidate_models(client):
    """Plain Flash and Flash-Lite models your key can use, newest first (Flash before Lite)."""
    import re
    names = []
    for m in client.models.list():
        actions = list(getattr(m, "supported_actions", None) or [])
        n = (getattr(m, "name", "") or "").replace("models/", "")
        if (not actions or "generateContent" in actions) and re.fullmatch(r"gemini-\d+(?:\.\d+)?-flash(?:-lite)?(?:-preview)?", n):
            names.append(n)
    key = lambda n: (not n.endswith("-preview"), tuple(int(x) for x in re.findall(r"\d+", n.split("-flash")[0])), "-lite" not in n)
    return sorted(set(names), key=key, reverse=True)                  # stable models first, then previews


def try_model(client, name):
    from google.genai import types
    resp = client.models.generate_content(model=name, contents="Reply with the single word OK.",
                                          config=types.GenerateContentConfig(temperature=0))
    return (resp.text or "").strip()[:20]


def run(title, fn):
    print(f"\n[{title}]", flush=True)
    t0 = time.time()
    try:
        out = fn()
        print(f"   OK in {time.time() - t0:.1f} s" + (f": {out}" if out else ""), flush=True)
        return True
    except Exception as e:
        print(f"   FAILED after {time.time() - t0:.1f} s: {str(e)[:300]}", flush=True)
        return False


def main():
    llm = GeminiLLM()
    print("1. Settings")
    if not llm.api_key:
        print("   GEMINI_API_KEY is missing. Put it in the .env file next to main.py, save it, and run this again.")
        return
    print(f"   key found ({len(llm.api_key)} characters), model setting: {llm.model}, timeout: {llm.timeout:.0f} s")

    def reach():
        import urllib.request
        import urllib.error
        try:
            urllib.request.urlopen("https://generativelanguage.googleapis.com", timeout=10)
        except urllib.error.HTTPError:
            pass                                      # any HTTP answer means we reached Google
        return "Google's Gemini servers are reachable"

    if not run("2. Can this computer reach Google's Gemini servers?", reach):
        print("\n   The connection to Google is blocked or very slow. Try another network (a phone hotspot is a good test),")
        print("   turn off any VPN or proxy, and run this again.")
        return

    from google import genai
    from google.genai import types
    client = genai.Client(api_key=llm.api_key, http_options=types.HttpOptions(timeout=TRY_SECONDS * 1000))

    def list_models():
        return f"newest stable Flash model for your key: {pick_flash_model(client)}"

    run("3. Ask Google which models your key can use", list_models)

    results = []

    def race():
        names = candidate_models(client)
        if not names:
            raise RuntimeError("No Flash models were listed for your key.")
        print(f"   trying up to {min(len(names), MAX_TRIES)} models, {TRY_SECONDS} s each: {', '.join(names[:MAX_TRIES])}", flush=True)
        for n in names[:MAX_TRIES]:
            t0 = time.time()
            try:
                text = try_model(client, n)
                results.append((time.time() - t0, n))
                print(f"     {n}: answered '{text}' in {time.time() - t0:.1f} s", flush=True)
            except Exception as e:
                print(f"     {n}: FAILED after {time.time() - t0:.1f} s ({str(e)[:90]})", flush=True)
        if not results:
            raise RuntimeError("None of the models answered in time.")
        return f"working models: {', '.join(n for _, n in results)}"

    if not run("4. Send one tiny question to several Flash models", race):
        print("\n   Nothing answered. The connection to Google works, but answers are not coming back.")
        print("   Try again in a few minutes, or on another network (a phone hotspot is a good test). If it keeps failing,")
        print("   send me this whole output.")
        return
    full = [n for _, n in results if "-lite" not in n]          # results are in the order tried: newest stable first
    best = full[0] if full else results[0][1]
    note = "" if full else "  (a Lite model: quicker and a little less capable, fine for this project)"
    print(f"\n   NEXT STEP: put this line in your .env file, save it, and restart:\n       GEMINI_MODEL={best}{note}")

    def embed():
        from backend.rag.embedder import SentenceEmbedder
        SentenceEmbedder().encode(["test sentence"])
        return "embedding model loaded and used"

    run("5. Load the embedding model (the first time this can take a while)", embed)
    print("\nDone. If every step says OK, run: python scripts/try_rag.py --ticker TCS")


if __name__ == "__main__":
    main()
