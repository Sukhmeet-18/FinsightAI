"""
RiskModel - the part of the risk model the rest of FinSight uses.

    rm = RiskModel()                                  # loads models/risk/*.json
    rm.forecast_ticker("TCS", close_series)           # one stock's risk forecast
    rm.forecast_covariance(prices)                    # covariance for the optimizer
    rm.portfolio_risk(weights, prices, capital)       # VaR / CVaR of a portfolio

Stocks without a trained model (or whose fit was not OK) fall back to their
recent historical volatility, so nothing breaks.
"""

import math
import os

import numpy as np
import pandas as pd
from pypfopt import risk_models
from scipy import stats

from .garch_model import (HORIZON, TRADING_DAYS, forecast, load_params,
                          t_quantile_es, to_log_returns)

MODELS_DIR = os.environ.get("FINSIGHT_MODELS_DIR", os.path.join("models", "risk"))
LIVE_FILE = "gjr_params_live.json"     # trained on ALL data - used by the app
EVAL_FILE = "gjr_params.json"          # trained on the training split only


class RiskModel:
    def __init__(self, params_path: str | None = None):
        if params_path is None:
            live = os.path.join(MODELS_DIR, LIVE_FILE)
            params_path = live if os.path.exists(live) else os.path.join(MODELS_DIR, EVAL_FILE)
        if not os.path.exists(params_path):
            raise FileNotFoundError(
                f"No trained risk model at {params_path}. Run scripts/train_risk_model.py first.")
        payload = load_params(params_path)
        self.path = params_path
        self.meta = payload.get("meta", {})
        self.records = {t: rec for t, rec in payload["models"].items() if rec.get("ok")}

    # ------------------------------------------------------------------
    def has_model(self, ticker: str) -> bool:
        return ticker in self.records

    def forecast_ticker(self, ticker: str, close: pd.Series, horizon: int = HORIZON,
                        alpha: float = 0.05, history_days: int = 1500) -> dict | None:
        """Risk forecast for one stock from its closing prices (None if no model)."""
        if ticker not in self.records:
            return None
        r = to_log_returns(close.dropna()).iloc[-history_days:]
        if len(r) < 100:
            return None
        out = forecast(r, self.records[ticker], horizon, alpha)
        out["ticker"] = ticker
        out["params"] = self.records[ticker]["params"]
        return out

    def forecast_vols(self, prices: pd.DataFrame, horizon: int = HORIZON) -> pd.Series:
        """
        Annualized forecast volatility per stock (decimal). Stocks without a
        model get their historical volatility over the given price window.
        """
        hist = np.log(prices).diff().std() * math.sqrt(TRADING_DAYS)
        vols = {}
        for t in prices.columns:
            fc = self.forecast_ticker(t, prices[t], horizon=horizon)
            vols[t] = fc["vol_annual"] if fc else float(hist[t])
        return pd.Series(vols)

    # ------------------------------------------------------------------
    def forecast_covariance(self, prices: pd.DataFrame, horizon: int = HORIZON) -> pd.DataFrame:
        """
        Forward-looking annual covariance matrix:  S = D * R * D
            R = correlation between stocks (Ledoit-Wolf shrinkage, recent prices)
            D = GJR-GARCH forecast volatility of each stock
        Correlations change slowly; volatility changes fast - this is where
        the risk model improves on a purely historical covariance.
        """
        cov_hist = risk_models.CovarianceShrinkage(prices).ledoit_wolf()
        sd = np.sqrt(np.diag(cov_hist))
        corr = cov_hist.values / np.outer(sd, sd)
        np.fill_diagonal(corr, 1.0)
        vols = self.forecast_vols(prices, horizon).reindex(prices.columns).values
        S = np.outer(vols, vols) * corr
        return pd.DataFrame(S, index=prices.columns, columns=prices.columns)

    # ------------------------------------------------------------------
    def portfolio_risk(self, weights: dict, prices: pd.DataFrame, capital: float | None = None,
                       alpha: float = 0.05, horizon: int = HORIZON) -> dict:
        """
        Forecast risk of a portfolio. Daily figures use the next-day forecast;
        the multi-day VaR uses the average forecast over the horizon.
        Tails use a Student-t whose nu is the weighted average of the holdings'
        nu (an approximation - state it in the report).
        """
        tickers = [t for t, w in weights.items() if w > 0]
        w = np.array([weights[t] for t in tickers])
        px = prices[tickers]

        S1 = self.forecast_covariance(px, horizon=1).values / TRADING_DAYS       # next-day
        Sh = self.forecast_covariance(px, horizon=horizon).values / TRADING_DAYS  # avg daily
        sigma_1d = float(math.sqrt(w @ S1 @ w))
        sigma_h = float(math.sqrt(w @ Sh @ w) * math.sqrt(horizon))

        nus = [self.records[t]["params"]["nu"] for t in tickers if t in self.records]
        nu = float(np.average([n for n in nus], weights=[weights[t] for t in tickers if t in self.records])) if nus else 8.0
        nu = max(nu, 3.0)
        q, es = t_quantile_es(alpha, nu)
        z = stats.norm.ppf(alpha)
        conf = int((1 - alpha) * 100)

        out = {
            "model": "GJR-GARCH(1,1) Student-t",
            "confidence": conf,
            "horizon_days": horizon,
            "vol_1d": round(sigma_1d, 5),
            "vol_annual_forecast": round(math.sqrt(w @ (Sh * TRADING_DAYS) @ w), 4),
            f"var_{conf}_1d": round(-sigma_1d * q, 5),
            f"cvar_{conf}_1d": round(-sigma_1d * es, 5),
            f"var_{conf}_{horizon}d": round(-sigma_h * z, 5),
            "coverage": f"{sum(t in self.records for t in tickers)}/{len(tickers)} holdings have a trained model",
        }
        if capital:
            out[f"var_{conf}_1d_amount"] = round(out[f"var_{conf}_1d"] * capital, 2)
            out[f"cvar_{conf}_1d_amount"] = round(out[f"cvar_{conf}_1d"] * capital, 2)
            out[f"var_{conf}_{horizon}d_amount"] = round(out[f"var_{conf}_{horizon}d"] * capital, 2)
        return out
