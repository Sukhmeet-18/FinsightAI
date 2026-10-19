"""
Walk-forward backtest - "would the robo-advisor actually have worked?"

Starting at `start`, every `rebalance_every` trading days:
    1. build the portfolio using ONLY data up to that day (no look-ahead)
    2. hold it until the next rebalance day
    3. pay a trading cost on what changed (turnover x cost)

Compared against:
    - Nifty 50 (buy and hold)
    - Equal weight: the same candidate stocks, equally weighted, same rebalancing
      (shows whether the OPTIMIZER adds value beyond simply picking the candidates)

If a risk model is used it must be trained on data that ends before `start`
(models/risk/gjr_params.json, not the live file), otherwise it has seen the future.
"""

import numpy as np
import pandas as pd

from backend.common.data_loader import window_prices
from .metrics import series_stats
from .optimizer import build_portfolio, select_candidates

COST = 0.001            # 0.1% of the traded amount (brokerage, STT, slippage - rough)


def _hold(weights: dict, table: pd.DataFrame, d0, d1, start_value: float) -> pd.Series:
    """Buy-and-hold value from d0 to d1 (inclusive)."""
    px = table.loc[table.index <= d1, list(weights)].ffill().loc[d0:]
    w = pd.Series(weights)
    units = w * start_value / px.iloc[0]
    return (px * units).sum(axis=1)


def _drifted(weights: dict, table: pd.DataFrame, d0, d1) -> dict:
    """Weights at d1 after prices moved since d0 (needed to measure turnover)."""
    px = table.loc[table.index <= d1, list(weights)].ffill().loc[[d0, d1]]
    grown = pd.Series(weights) * (px.iloc[1] / px.iloc[0])
    return (grown / grown.sum()).to_dict()


def _turnover(old: dict, new: dict) -> float:
    keys = set(old) | set(new)
    return sum(abs(new.get(k, 0) - old.get(k, 0)) for k in keys)


def run_backtest(table: pd.DataFrame, benchmark: pd.Series, cap_of: dict, profile: str,
                 start, end=None, rebalance_every: int = 63, lookback_years: float = 3.0,
                 cost: float = COST, risk_model=None, always_include=None, rf: float = 0.065):
    """
    table     : FULL price history of the universe (load_close_table)
    benchmark : FULL Nifty history
    Returns (summary_dict, daily_values_dataframe).
    """
    end = pd.Timestamp(end) if end is not None else table.index.max()
    days = table.index[(table.index >= pd.Timestamp(start)) & (table.index <= end)]
    rebal_days = list(days[::rebalance_every])
    if len(rebal_days) < 2:
        raise ValueError("Backtest period too short.")

    robo_val, eq_val = 1.0, 1.0
    robo_w_prev, eq_w_prev = {}, {}
    robo_parts, eq_parts = [], []
    turnover_total, n_holdings, notes = 0.0, [], []

    for i, d0 in enumerate(rebal_days):
        d1 = rebal_days[i + 1] if i + 1 < len(rebal_days) else days[-1]
        if d1 <= d0:
            break
        prices = window_prices(table, end=d0, lookback_years=lookback_years)
        bench = benchmark.reindex(prices.index).ffill().bfill()

        res = build_portfolio(prices, cap_of, profile, 1.0, benchmark=bench,
                              always_include=always_include, rf=rf, risk_model=risk_model)
        w_new = {a["ticker"]: a["weight"] for a in res["allocation"]}
        s = sum(w_new.values()); w_new = {k: v / s for k, v in w_new.items()}
        notes += [f"{d0.date()}: {n}" for n in res["notes"]]

        cands = select_candidates(prices, cap_of, always_include=always_include)
        eq_new = {t: 1 / len(cands) for t in cands}

        # trading costs on the change
        to = _turnover(robo_w_prev, w_new)
        turnover_total += to
        robo_val *= (1 - cost * to)
        eq_val *= (1 - cost * _turnover(eq_w_prev, eq_new))

        rv = _hold(w_new, table, d0, d1, robo_val)
        ev = _hold(eq_new, table, d0, d1, eq_val)
        robo_parts.append(rv if i == 0 else rv.iloc[1:])
        eq_parts.append(ev if i == 0 else ev.iloc[1:])
        robo_val, eq_val = float(rv.iloc[-1]), float(ev.iloc[-1])
        robo_w_prev, eq_w_prev = _drifted(w_new, table, d0, d1), _drifted(eq_new, table, d0, d1)
        n_holdings.append(len(w_new))

    robo = pd.concat(robo_parts)
    eq = pd.concat(eq_parts)
    nifty = benchmark.reindex(robo.index).ffill().bfill()
    nifty = nifty / nifty.iloc[0]
    values = pd.DataFrame({"robo_advisor": robo, "equal_weight": eq, "nifty50": nifty})

    summary = {
        "profile": profile,
        "start": str(robo.index[0].date()), "end": str(robo.index[-1].date()),
        "rebalances": len(n_holdings), "rebalance_every_days": rebalance_every,
        "avg_holdings": round(float(np.mean(n_holdings)), 1),
        "avg_turnover_per_rebalance": round(turnover_total / len(n_holdings), 3),
        "trading_cost": cost,
        "used_risk_model": risk_model is not None,
        "robo_advisor": series_stats(robo, rf),
        "equal_weight": series_stats(eq, rf),
        "nifty50": series_stats(nifty, rf),
        "notes": notes[:10],
    }
    return summary, values
