"""Quick health check for Groq. It tells you which step is slow or broken and which model to use.

Run from the project folder:
    python scripts/check_groq.py
Nothing here prints your key.
"""
import os
import sys
import time

sys.path.insert(0, os.getcwd())

from backend.rag.llm import GROQ_PREFERRED, GroqLLM, pick_groq_model     # noqa: E402  (also loads .env)

TRY_SECONDS, MAX_TRIES = 25, 3


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
    llm = GroqLLM()
    llm.timeout = TRY_SECONDS
    print("1. Settings")
    if not llm.api_key:
        print("   GROQ_API_KEY is missing. Get a free key at console.groq.com/keys, put it in the .env file next to main.py, save it, and run this again.")
        return
    print(f"   key found ({len(llm.api_key)} characters{'' if llm.api_key.startswith('gsk_') else ', but Groq keys normally start with gsk_'}), "
          f"LLM_PROVIDER={os.environ.get('LLM_PROVIDER') or '(not set)'}, model setting: {llm.model}")
    ids = []

    def listing():
        ids.extend(llm.list_models())
        return f"{len(ids)} models listed, the app would choose: {pick_groq_model(ids)}"

    if not run("2. Ask Groq which models your key can use", listing):
        print("\n   Groq could not be reached or rejected the key. Check the key, try another network (a phone hotspot is a good test),")
        print("   turn off any VPN or proxy, and run this again.")
        return
    names = [m for m in GROQ_PREFERRED if m in ids]
    pick = pick_groq_model(ids)
    if pick and pick not in names:
        names.append(pick)
    if not names:
        print("\n   No chat models were found for your key.")
        return
    worked = []

    def race():
        print(f"   trying up to {min(len(names), MAX_TRIES)} models, {TRY_SECONDS} s each: {', '.join(names[:MAX_TRIES])}", flush=True)
        for n in names[:MAX_TRIES]:
            t0 = time.time()
            try:
                r = llm._chat(n, "Reply with the single word OK.")
                if r.status_code != 200:
                    raise RuntimeError(llm._problem(r))
                text = (r.json()["choices"][0]["message"]["content"] or "").strip()[:20]
                worked.append(n)
                print(f"     {n}: answered '{text}' in {time.time() - t0:.1f} s", flush=True)
            except Exception as e:
                print(f"     {n}: FAILED after {time.time() - t0:.1f} s ({str(e)[:100]})", flush=True)
        if not worked:
            raise RuntimeError("None of the models answered.")
        return f"working models: {', '.join(worked)}"

    if not run("3. Send one tiny question to Groq", race):
        print("\n   Nothing answered. If the message above mentions a rate limit, wait a minute and run this again. Otherwise send me this whole output.")
        return
    print("\n   NEXT STEP: your .env file should contain these three lines (keep your real key), then save and restart:")
    print("       LLM_PROVIDER=groq")
    print("       GROQ_API_KEY=your-real-key")
    print(f"       GROQ_MODEL={worked[0]}")
    print("\nDone. Then run: python scripts/try_rag.py --ticker TCS")


if __name__ == "__main__":
    main()
