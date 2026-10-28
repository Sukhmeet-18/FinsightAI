# FinSight AI

An integrated, explainable platform for financial analysis, document-grounded question answering and risk-aligned portfolio advice on NSE-listed companies. Built as a B.Tech major project at GTBIT (CSE-DS).

> Educational project. Nothing here is investment advice.

## What it does

| Part | What it gives you |
|---|---|
| **Companies** | Five NSE companies with live price, growth, margin, ROE, a 0 to 100 score, and a learned Buy / Hold / Sell "model view" marked experimental |
| **Risk engine** | GJR-GARCH volatility forecasts, VaR and CVaR for a stock or a portfolio |
| **Portfolio Advisor** | Five quiz questions and an amount give a portfolio in whole shares, with risk numbers, crash replays, a three-year record and the odds of reaching a goal |
| **Ask a Report** | Questions about a company's annual report, answered from the report with the page each answer came from |
| **How it works** | A 45-second animation of how data moves through the platform (`frontend/src/howitworks/scene.js`); an optional `frontend/public/how-it-works.mp4` adds a download button |
| **Say vs. Show** | Contradiction detector: compares the tone of a company's annual report (FinBERT) with the trend in its numbers and flags when they disagree |

## Project layout

```
main.py                  FastAPI app (company overview, router wiring)
backend/
  common/                data loading helpers
  risk_model/            GJR-GARCH model, service, routes
  classifier/            saved Buy / Hold / Sell model and model view
  robo_advisor/          quiz, optimiser, risk measures, stress tests, Monte Carlo, backtest, routes
  rag/                   PDF reading, embeddings, FAISS index, Groq or Gemini, routes
  detector/              contradiction detector: tone (FinBERT), trend, verdicts, routes
frontend/                React + Vite + Tailwind dashboard
scripts/                 build_rag_index.py, try_rag.py, run_detector.py, check_groq.py, check_gemini.py, backtest_robo.py
tests/                   automated tests (report assistant, detector)
finsight_fetch_data.py   downloads prices and yearly results into data/
train_classifier.py      trains the Buy / Hold / Sell model into models/
reports/robo/            walk-forward backtest results
data/ models/            saved prices, results and trained models
documents/<COMPANY>/     annual report PDFs (not committed)
rag_store/               search indexes built from the PDFs (not committed)
```

## Run it locally

You need Python 3.10 and Node 18 or newer.

**1. Backend** (from this folder)

```
python -m venv Minor
Minor\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The API is then at http://127.0.0.1:8000 and its documentation at http://127.0.0.1:8000/docs.

**2. Frontend**

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Set up the report assistant

1. Put one annual report PDF in each company folder, for example `documents/TCS/report.pdf`. Folder names: `RELIANCE`, `TCS`, `HINDUNILVR` (or `HUL`), `MARUTI`, `ITC`. Any PDF file name works.
2. Create a file named `.env` next to `main.py`. Use **Groq** (fast, free tier, key from console.groq.com/keys):

   ```
   LLM_PROVIDER=groq
   GROQ_API_KEY=your-key-here
   # GROQ_MODEL=openai/gpt-oss-120b     (optional; the app finds a working model by itself)
   ```

   or **Gemini** (key from Google AI Studio):

   ```
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=your-key-here
   # GEMINI_MODEL=gemini-3.8-flash      (optional; the app finds a working model by itself)
   ```

   Check that it works with `python scripts/check_groq.py` or `python scripts/check_gemini.py`.

3. Build the search indexes (the first run downloads a 130 MB embedding model):

   ```
   python scripts/build_rag_index.py
   python scripts/try_rag.py --ticker TCS
   ```

## Tests and evaluation

```
pip install pytest reportlab httpx
python -m pytest tests               # 52 tests: robo-advisor, report assistant, detector
python scripts/run_detector.py       # contradiction detector on the five reports, writes rag_store/detector.json
python scripts/backtest_robo.py      # robo-advisor walk-forward backtest, writes reports/robo/
```

## Main API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /companies/overview` | Five companies with live data, score, label and model view |
| `GET /risk/forecast/{ticker}` | Volatility, VaR and CVaR for one stock |
| `POST /risk/portfolio` | The same for a portfolio of weights |
| `GET /portfolio/questions` | The five quiz questions |
| `POST /portfolio/recommend` | Portfolio, risk, crash replays, past record and goal odds |
| `POST /rag/ask` | An answer from a company's report, with page sources |
| `GET /rag/companies` | Which reports have been indexed |
| `GET /detector/summary` | Tone, trend and verdict for each company (run `scripts/run_detector.py` first) |

## Data and honesty notes

- Prices and yearly results come from Yahoo Finance through `yfinance`, an unofficial feed. The Portfolio Advisor uses a saved snapshot of the data (1 October 2026), while the Companies screen is live.
- The stock universe is today's index members, so results are affected by survivorship bias.
- Expected returns in the advisor come from CAPM (an assumption, not a forecast), and goal odds depend on it.
- Full results, caveats and how to reproduce them are in the project report.

## Team

Paridhi Pandey, Sukhmeet Kaur, Harshal Chauhan, Satyam Singh Negi. Guide: Ms. Debleena Mitra, Department of IT, GTBIT.
