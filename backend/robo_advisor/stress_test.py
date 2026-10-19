"""
Stress test - "what if a past crash happened while I held this portfolio?"

Buys the portfolio on the day the Nifty peaked before each crash and holds it
to the day the Nifty bottomed. Reports the loss, the worst point inside the
period, how long it took to get back to the starting value, and the Nifty's
loss over the same days for comparison.

Stocks that were not listed yet at the start are left out and the rest are
re-weighted; `coverage` says what share of the portfolio could be tested.
Dates are the Nifty 50's approximate peak and bottom for each event.
"""

import pandas as pd

from .metrics import portfolio_value

SCENARIOS = [
    {"name": "Global Financial Crisis", "start": "2008-01-08", "end": "2009-03-09"},
    {"name": "2015-16 slowdown",        "start": "2015-03-03", "end": "2016-02-29"},
    {"name": "COVID-19 crash",          "start": "2020-01-14", "end": "2020-03-23"},
    {"name": "2022 sell-off",           "start": "2021-10-18", "end": "2022-06-17"},
]
MIN_COVERAGE = 0.5      # need at least half the portfolio to have existed


def _window(series_or_frame, start, end):
    return series_or_frame.loc[(series_or_frame.index >= start) & (series_or_frame.index <= end)]


def run_stress_tests(weights: dict, full_prices: pd.DataFrame, benchmark: pd.Series,
                     capital: float | None = None, scenarios=SCENARIOS) -> list[dict]:
    """
    full_prices : FULL history (load_close_table), not a 3-year window.
    benchmark   : full Nifty history.
    """
    results = []
    for sc in scenarios:
        start, end = pd.Timestamp(sc["start"]), pd.Timestamp(sc["end"])
        px = _window(full_prices, start, end)
        row = {"event": sc["name"], "start": sc["start"], "end": sc["end"]}
        if px.empty:
            results.append({**row, "status": "no data for this period"})
            continue

        first = px.iloc[0]
        available = [t for t in weights if t in px.columns and pd.notna(first.get(t))]
        coverage = sum(weights[t] for t in available) / sum(weights.values())
        row["coverage"] = round(coverage, 3)
        if coverage < MIN_COVERAGE:
            results.append({**row, "status": "not enough holdings existed then"})
            continue

        value = portfolio_value({t: weights[t] for t in available}, px)
        loss = float(value.iloc[-1] / value.iloc[0] - 1)
        worst = float((value / value.cummax() - 1).min())

        # how long until it got back to the starting value (look past the end date)
        after = portfolio_value({t: weights[t] for t in available},
                                full_prices.loc[full_prices.index >= start])
        if loss >= 0:
            recovery_days = 0                      # ended above where it started
        else:
            back = after[(after.index > end) & (after >= after.iloc[0])]
            recovery_days = int((back.index[0] - end).days) if len(back) else None

        b = _window(benchmark, start, end).dropna()
        nifty_loss = float(b.iloc[-1] / b.iloc[0] - 1) if len(b) > 1 else None

        row.update({
            "status": "ok",
            "portfolio_return": round(loss, 4),
            "worst_drawdown": round(worst, 4),
            "nifty_return": round(nifty_loss, 4) if nifty_loss is not None else None,
            "vs_nifty": round(loss - nifty_loss, 4) if nifty_loss is not None else None,
            "days_to_recover": recovery_days,
        })
        if capital:
            # assumes the untested part behaved like the tested part (see coverage)
            row["estimated_amount_change"] = round(loss * capital, 2)
        results.append(row)
    return results
