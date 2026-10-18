"""
FastAPI endpoints for the risk model.

Register in backend/main.py:
    from backend.risk_model.router import router as risk_router
    app.include_router(risk_router, prefix="/risk", tags=["risk"])

Endpoints:
    GET  /risk/forecast/{ticker}   -> next-day + next-month risk of one stock
    POST /risk/portfolio           -> VaR / CVaR of a given set of weights
"""

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.common.data_loader import DATA_DIR, load_prices, read_close
from .service import RiskModel

router = APIRouter()
_model: RiskModel | None = None


def get_model() -> RiskModel:
    global _model
    if _model is None:
        _model = RiskModel()          # loaded once, then reused
    return _model


@router.get("/forecast/{ticker}")
def forecast_ticker(ticker: str):
    ticker = ticker.upper()
    path = os.path.join(DATA_DIR, "prices", f"{ticker}.csv")
    if not os.path.exists(path):
        raise HTTPException(404, f"No price data for {ticker}")
    out = get_model().forecast_ticker(ticker, read_close(path))
    if out is None:
        raise HTTPException(404, f"No trained risk model for {ticker}")
    out.pop("variance_path_daily", None)
    return out


class PortfolioIn(BaseModel):
    weights: dict[str, float]          # {"TCS": 0.2, "ITC": 0.3, ...}
    capital: float | None = None


@router.post("/portfolio")
def portfolio_risk(body: PortfolioIn):
    tickers = [t.upper() for t in body.weights]
    prices = load_prices(tickers, lookback_years=3)
    missing = set(tickers) - set(prices.columns)
    if missing:
        raise HTTPException(400, f"Not enough price data for: {sorted(missing)}")
    weights = {t.upper(): w for t, w in body.weights.items()}
    return get_model().portfolio_risk(weights, prices, body.capital)
