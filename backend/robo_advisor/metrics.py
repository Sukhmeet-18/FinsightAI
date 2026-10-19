"""
Historical performance and risk of a portfolio (looking BACKWARD).

    How would these weights have done over the price window we have?
    - CAGR (yearly growth), volatility, Sharpe, Sortino
    - max drawdown (worst fall from a peak) and when it happened
    - beta vs Nifty, and return vs Nifty
    - historical 1-day VaR / CVaR (from real past days, no model)

The GJR-GARCH risk model gives the FORWARD-looking risk; this gives the
backward-looking track record. The dashboard can show both.
"""

import math

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def portfolio_value(weights: dict, prices: pd.DataFrame, start_value: float = 1.0) -> pd.Series:
    """
    Value of a buy-and-hold portfolio bought on the first day with these weights.
    Stocks missing on day one are ignored and the rest re-weighted.
    """
    px = prices[[t for t in weights if t in prices.columns]].dropna(how="all")
    first = px.iloc[0]
    held = [t for t in px.columns if pd.notna(first[t])]
    w = pd.Series({t: weights[t] for t in held})
    w = w / w.sum()
    units = w * start_value / first[held]
    return (px[held].ffill() * units).sum(axis=1)


def max_drawdown(value: pd.Series) -> dict:
    peak = value.cummax()
    dd = value / peak - 1
    trough = dd.idxmin()
    peak_date = value.loc[:trough].idxmax()
    recovered = value.loc[trough:][value.loc[trough:] >= value.loc[peak_date]]
    return {"max_drawdown": float(dd.min()),
            "peak_date": str(peak_date.date()),
            "trough_date": str(trough.date()),
            "recovery_date": str(recovered.index[0].date()) if len(recovered) else None}


def series_stats(value: pd.Series, rf: float = 0.065) -> dict:
    """CAGR, volatility, Sharpe, Sortino and max drawdown of any value series."""
    rets = value.pct_change().dropna()
    years = (value.index[-1] - value.index[0]).days / 365.25
    cagr = (value.iloc[-1] / value.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(TRADING_DAYS)
    down = rets[rets < 0].std() * math.sqrt(TRADING_DAYS)
    return {"cagr": round(cagr, 4), "volatility": round(vol, 4),
            "sharpe": round((cagr - rf) / vol, 3) if vol > 0 else None,
            "sortino": round((cagr - rf) / down, 3) if down > 0 else None,
            "max_drawdown": round(float((value / value.cummax() - 1).min()), 4),
            "total_return": round(float(value.iloc[-1] / value.iloc[0] - 1), 4)}


def historical_metrics(weights: dict, prices: pd.DataFrame, benchmark: pd.Series | None = None,
                       rf: float = 0.065, capital: float | None = None) -> dict:
    value = portfolio_value(weights, prices)
    rets = value.pct_change().dropna()
    years = (value.index[-1] - value.index[0]).days / 365.25

    cagr = (value.iloc[-1] / value.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(TRADING_DAYS)
    downside = rets[rets < 0].std() * math.sqrt(TRADING_DAYS)
    var95 = -float(np.percentile(rets, 5))
    cvar95 = -float(rets[rets <= -var95].mean())

    out = {
        "period_start": str(value.index[0].date()),
        "period_end": str(value.index[-1].date()),
        "cagr": round(cagr, 4),
        "volatility": round(vol, 4),
        "sharpe": round((cagr - rf) / vol, 3) if vol > 0 else None,
        "sortino": round((cagr - rf) / downside, 3) if downside > 0 else None,
        "hist_var_95_1d": round(var95, 5),
        "hist_cvar_95_1d": round(cvar95, 5),
        "best_day": round(float(rets.max()), 4),
        "worst_day": round(float(rets.min()), 4),
        **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in max_drawdown(value).items()},
    }
    if capital:
        out["hist_var_95_1d_amount"] = round(var95 * capital, 2)
        out["max_drawdown_amount"] = round(out["max_drawdown"] * capital, 2)

    if benchmark is not None:
        b = benchmark.reindex(value.index).ffill().bfill()
        b_rets = b.pct_change().reindex(rets.index)
        b_cagr = (b.iloc[-1] / b.iloc[0]) ** (1 / years) - 1
        out["beta"] = round(float(rets.cov(b_rets) / b_rets.var()), 3)
        out["nifty_cagr"] = round(b_cagr, 4)
        out["excess_return_vs_nifty"] = round(cagr - b_cagr, 4)
        out["nifty_max_drawdown"] = round(float((b / b.cummax() - 1).min()), 4)
    return out


def growth_series(weights: dict, prices: pd.DataFrame, benchmark: pd.Series | None,
                  start_value: float = 100.0, every: int = 5) -> list[dict]:
    """Portfolio vs Nifty growth of 100, for the dashboard line chart."""
    value = portfolio_value(weights, prices, start_value)
    rows = []
    b = None
    if benchmark is not None:
        b = benchmark.reindex(value.index).ffill().bfill()
        b = b / b.iloc[0] * start_value
    for i, (d, v) in enumerate(value.items()):
        if i % every == 0 or i == len(value) - 1:
            row = {"date": str(d.date()), "portfolio": round(float(v), 2)}
            if b is not None:
                row["nifty"] = round(float(b.loc[d]), 2)
            rows.append(row)
    return rows
