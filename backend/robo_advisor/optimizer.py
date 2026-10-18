"""
Robo-advisor core - Mean-Variance Optimization (Markowitz).

Pipeline:
    prices -> pick candidates -> expected returns (mu) + covariance (S)
           -> optimize for the user's risk profile (with limits) -> allocation
           -> forecast risk of the final portfolio (VaR / CVaR)

Stability fixes:
    1. mu from CAPM: rf + beta * (assumed equity risk premium).
    2. S from the GJR-GARCH risk model when available (forecast volatility x
       shrunk correlation); otherwise Ledoit-Wolf shrinkage of past returns.
"""

import math
import numpy as np
import pandas as pd
from pypfopt import EfficientFrontier, expected_returns, risk_models, objective_functions

TRADING_DAYS = 252
RISK_FREE_RATE = 0.065       # annual; set to the current 91-day T-bill yield (RBI site)
EQUITY_RISK_PREMIUM = 0.07   # assumed extra yearly return of Indian equities over rf
                             # (typical estimates 6-8%; state this in the report)

PROFILES = {
    "conservative": {"objective": "min_volatility", "max_weight": 0.15,
                     "cap_upper": {"small": 0.10}, "cap_lower": {"large": 0.50}},
    "balanced":     {"objective": "max_sharpe", "max_weight": 0.15,
                     "cap_upper": {"small": 0.25}, "cap_lower": {"large": 0.30}},
    "aggressive":   {"objective": "efficient_risk", "target_volatility": 0.22,
                     "max_weight": 0.20, "cap_upper": {"small": 0.40}, "cap_lower": {}},
}


# ---------------------------------------------------------------------------
def select_candidates(prices, cap_of, n_per_tier=10, scores=None, always_include=None):
    """Top n stocks per cap tier (by ML score if given, else past Sharpe)."""
    rets = prices.pct_change().dropna()
    if scores is None:
        scores = (rets.mean() / rets.std() * math.sqrt(TRADING_DAYS)).to_dict()
    chosen = set(always_include or []) & set(prices.columns)
    for tier in ("large", "mid", "small"):
        tier_stocks = [t for t in prices.columns if cap_of.get(t) == tier]
        ranked = sorted(tier_stocks, key=lambda t: scores.get(t, -np.inf), reverse=True)
        chosen.update(ranked[:n_per_tier])
    return sorted(chosen)


def compute_betas(prices, benchmark):
    rets = prices.pct_change().dropna()
    mkt = benchmark.reindex(prices.index).ffill().bfill().pct_change().reindex(rets.index)
    return rets.apply(lambda col: col.cov(mkt)) / mkt.var()


def estimate_inputs(prices, benchmark=None, method="capm", rf=RISK_FREE_RATE,
                    erp=EQUITY_RISK_PREMIUM, risk_model=None):
    """
    Returns (mu, S, cov_source).
      method: "capm" (rf + beta*ERP, recommended) | "capm_realized" | "mean" | "ema"
      risk_model: a RiskModel -> S uses GJR-GARCH forecast volatility.
    """
    if method == "capm" and benchmark is not None:
        mu = rf + compute_betas(prices, benchmark) * erp
    elif method == "capm_realized" and benchmark is not None:
        market = benchmark.reindex(prices.index).ffill().bfill().to_frame("mkt")
        mu = expected_returns.capm_return(prices, market_prices=market, risk_free_rate=rf)
    elif method == "ema":
        mu = expected_returns.ema_historical_return(prices)
    else:
        mu = expected_returns.mean_historical_return(prices)

    if risk_model is not None:
        S, source = risk_model.forecast_covariance(prices), "GJR-GARCH forecast"
    else:
        S, source = risk_models.CovarianceShrinkage(prices).ledoit_wolf(), "Ledoit-Wolf historical"
    return mu, S, source


# ---------------------------------------------------------------------------
def _check_feasible(tickers, cap_of, cfg):
    maxw = cfg["max_weight"]
    if len(tickers) * maxw < 1:
        raise ValueError(f"Need at least {math.ceil(1 / maxw)} stocks for a {maxw:.0%} "
                         f"per-stock limit; got {len(tickers)}.")
    for tier, low in cfg["cap_lower"].items():
        if sum(cap_of.get(t) == tier for t in tickers) * maxw < low:
            raise ValueError(f"Not enough {tier}-cap stocks for the {low:.0%} minimum.")


def _new_frontier(mu, S, cap_of, cfg, l2_gamma):
    ef = EfficientFrontier(mu, S, weight_bounds=(0, cfg["max_weight"]))
    ef.add_sector_constraints({t: cap_of.get(t, "unknown") for t in mu.index},
                              cfg["cap_lower"], cfg["cap_upper"])
    if l2_gamma > 0:
        ef.add_objective(objective_functions.L2_reg, gamma=l2_gamma)
    return ef


def optimize(mu, S, cap_of, profile, rf=RISK_FREE_RATE, l2_gamma=0.0):
    cfg = PROFILES[profile]
    _check_feasible(list(mu.index), cap_of, cfg)
    notes = []
    ef = _new_frontier(mu, S, cap_of, cfg, l2_gamma)
    try:
        if cfg["objective"] == "max_sharpe":
            ef.max_sharpe(risk_free_rate=rf)
        elif cfg["objective"] == "efficient_risk":
            ef.efficient_risk(target_volatility=cfg["target_volatility"])
        else:
            ef.min_volatility()
    except Exception as e:
        notes.append(f"'{cfg['objective']}' was not possible ({e}); used minimum volatility instead.")
        ef = _new_frontier(mu, S, cap_of, cfg, l2_gamma)
        ef.min_volatility()
    weights = {t: w for t, w in ef.clean_weights(cutoff=1e-4).items() if w > 0}
    return weights, ef.portfolio_performance(risk_free_rate=rf), notes


# ---------------------------------------------------------------------------
def build_portfolio(prices, cap_of, profile, capital, benchmark=None, n_per_tier=10,
                    scores=None, always_include=None, rf=RISK_FREE_RATE,
                    return_method="capm", risk_model=None):
    """Main entry point - returns a dict in the agreed API shape."""
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile '{profile}'. Use one of {list(PROFILES)}.")

    candidates = select_candidates(prices, cap_of, n_per_tier, scores, always_include)
    px = prices[candidates]
    mu, S, cov_source = estimate_inputs(px, benchmark, return_method, rf, risk_model=risk_model)
    weights, (exp_ret, vol, sharpe), notes = optimize(mu, S, cap_of, profile, rf)

    fvol = risk_model.forecast_vols(px[list(weights)]) if risk_model is not None else None
    latest = px.iloc[-1]
    allocation = []
    for t, w in sorted(weights.items(), key=lambda kv: kv[1], reverse=True):
        amount = w * capital
        row = {"ticker": t, "cap": cap_of.get(t), "weight": round(w, 4),
               "amount": round(amount, 2), "shares": int(amount // latest[t]),
               "price": round(float(latest[t]), 2)}
        if fvol is not None:
            row["forecast_vol_annual"] = round(float(fvol[t]), 4)
        allocation.append(row)

    cap_split = {}
    for a in allocation:
        cap_split[a["cap"]] = round(cap_split.get(a["cap"], 0) + a["weight"], 4)

    result = {
        "profile": profile, "capital": capital, "as_of": str(px.index[-1].date()),
        "allocation": allocation, "cap_split": cap_split,
        "metrics": {"exp_return": round(exp_ret, 4), "volatility": round(vol, 4),
                    "sharpe": round(sharpe, 3), "covariance_source": cov_source},
        "notes": notes,
    }
    if risk_model is not None:
        result["risk_forecast"] = risk_model.portfolio_risk(weights, px, capital)
    return result


def frontier_points(mu, S, cap_of, profile="balanced", n_points=20):
    cfg = PROFILES[profile]
    ef = _new_frontier(mu, S, cap_of, cfg, 0.0)
    ef.min_volatility()
    r_min, r_max = ef.portfolio_performance()[0], float(mu.max()) * 0.98
    points = []
    for target in np.linspace(r_min, r_max, n_points):
        try:
            ef = _new_frontier(mu, S, cap_of, cfg, 0.0)
            ef.efficient_return(target_return=float(target))
            r, v, _ = ef.portfolio_performance()
            points.append({"volatility": round(v, 4), "return": round(r, 4)})
        except Exception:
            continue
    return points
