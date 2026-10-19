from fastapi import FastAPI, HTTPException
import yfinance as yf
import time
from backend.classifier.service import model_view

from fastapi.middleware.cors import CORSMiddleware # TO allow CORS eplciitly
from backend.risk_model.router import router as risk_router
from pydantic import BaseModel
from backend.common.data_loader import load_universe, load_prices, load_benchmark
from backend.robo_advisor.optimizer import build_portfolio
from backend.risk_model.router import get_model
from backend.robo_advisor.risk_profile import score_risk_profile, QUESTIONS
TICKERS=["RELIANCE.NS","TCS.NS","HINDUNILVR.NS","MARUTI.NS","ITC.NS"]
CORE = ["RELIANCE", "TCS", "ITC", "MARUTI", "HINDUNILVR"]
_robo_data={}
_cache={}
_overview_cache = {"t": 0, "data": None}
CACHE_TTL_SECONDS=300

app=FastAPI()

app.include_router(risk_router, prefix="/risk", tags=["risk"])



#allowing cors explicitly

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"]
)


#Functions

def get_roe_fallback(stock):
    try:
        net_income= stock.financials.loc["Net Income"].iloc[0]
        equity=stock.balance_sheet.loc["Stockholders Equity"].iloc[0]
        return net_income/equity
    except(KeyError,IndexError):
        return None

def get_metrics(ticker:str):
    stock=yf.Ticker(ticker)
    info=stock.info

    roe = info.get("returnOnEquity")
    if roe is None:
        roe = get_roe_fallback(stock)

    return {
        "ticker": ticker,
        "name": info.get("longName", ticker),
        "revenue_growth": info.get("revenueGrowth"),
        "profit_margin": info.get("profitMargins"),
        "roe": roe,
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
    }

def normalize(values):
    lo=min(values)
    hi=max(values)
    if hi==lo:
        return[0.5 for _ in values]
    return[(v-lo)/(hi-lo) for v in values]


def score_to_label(score):
    if score >= 0.65:
        return "Strong Buy"
    elif score >=0.5:
        return "Buy"
    elif score >=0.35:
        return "Hold"
    else:
        return "Sell"


def _robo_inputs():
    if not _robo_data:
        cap_of=load_universe()
        prices=load_prices(list(cap_of),lookback_years=3)
        _robo_data["cap_of"]=cap_of
        _robo_data["prices"]=prices
        _robo_data["bench"]=load_benchmark(index=prices.index)
    return _robo_data

class RoboIn(BaseModel):
    answers:list[int]
    capital:float=500000

#APIS
@app.get("/company/{ticker}")
def get_company(ticker:str):
    return get_metrics(ticker)

@app.get("/companies/metrics")
def get_all_metrics():
    return[get_metrics(t) for t in TICKERS]


@app.get("/")
def root(): 
    return{"status":"ok"}

@app.get("/companies")
def list_companies():
    return{"tickers":TICKERS}


@app.get("/companies/score")
def get_scores():
    metrics=[get_metrics(t) for t in TICKERS]

    revenue_growth=normalize([m["revenue_growth"] for m in metrics])
    profit_margin=normalize([m["profit_margin"] for m in metrics])
    roe=normalize([m["roe"] for m in metrics])

    w1,w2,w3=0.4,0.3,0.3 

    scores=[]
    for i,m in enumerate(metrics):
        score= w1*revenue_growth[i] + w2 * profit_margin[i] + w3 * roe[i]
        scores.append({"ticker":m["ticker"],"score":round(score,3),"label":score_to_label(score)})

    return scores


@app.get("/robo/questions")
def robo_questions():
    return QUESTIONS


@app.post("/robo/portfolio")
def robo_portfolio(body:RoboIn):
    try:
        profile,score=score_risk_profile(body.answers)
    except ValueError as e:
        raise HTTPException(400,str (e))
    d=_robo_inputs()
    try:
        result = build_portfolio(d["prices"], d["cap_of"], profile, body.capital,
                                 benchmark=d["bench"], always_include=CORE,
                                 risk_model=get_model())
    except ValueError as e:
        raise HTTPException(400, str(e))
    result["quiz_score"] = score
    return result





@app.get("/companies/overview")
def companies_overview():
    # one call for the dashboard: metrics + score + label, cached for 5 minutes
    if _overview_cache["data"] and time.time() - _overview_cache["t"] < 60:
        return _overview_cache["data"]

    metrics = [get_metrics(t) for t in TICKERS]
    rg = normalize([m["revenue_growth"] for m in metrics])
    pm = normalize([m["profit_margin"] for m in metrics])
    ro = normalize([m["roe"] for m in metrics])

    out = []
    for i, m in enumerate(metrics):
        s = 0.4 * rg[i] + 0.3 * pm[i] + 0.3 * ro[i]
        out.append({**m, "score": round(s * 100), "label": score_to_label(s),
                    "model": model_view(m["ticker"].replace(".NS", ""))})
    for i, m in enumerate(metrics):
        s = 0.4 * rg[i] + 0.3 * pm[i] + 0.3 * ro[i]
        out.append({**m, "score": round(s * 100), "label": score_to_label(s),
                    "model": model_view(m["ticker"].replace(".NS", "")),
                    "fetched_at": int(time.time())})

    _overview_cache["t"] = time.time()
    _overview_cache["data"] = out
    return out



