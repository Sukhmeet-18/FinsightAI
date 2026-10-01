from fastapi import FastAPI
import yfinance as yf
from fastapi.middleware.cors import CORSMiddleware # TO allow CORS eplciitly
TICKERS=["RELIANCE.NS","TCS.NS","HINDUNILVR.NS","MARUTI.NS","ITC.NS"]

_cache={}
CACHE_TTL_SECONDS=300

app=FastAPI()



#allowing cors explicitly

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    aloow_header=["*"]
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




