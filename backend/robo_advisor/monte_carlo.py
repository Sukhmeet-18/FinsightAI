"""
Monte Carlo goal projection - "what are my chances of reaching my goal?"

Simulates thousands of possible futures for the portfolio, month by month,
with an optional monthly top-up (SIP), and counts how many reach the goal.

Two methods:
  "bootstrap" (default) - each simulated month is a random real 21-day stretch
        of the portfolio's own history. Keeps fat tails and the way wild days
        cluster together. Its average growth is shifted to the expected return
        given (from the optimizer), so a lucky bull market in the data does not
        make every goal look easy.
  "normal" - monthly returns from a bell curve with the same mean and
        volatility. Simpler, but underestimates crashes. Useful as a comparison.

All amounts are in rupees of the future (nominal). Set `inflation` to express
the goal in today's money instead.
"""

import math

import numpy as np
import pandas as pd

TRADING_DAYS = 252
BLOCK = 21                      # trading days per simulated month


def portfolio_daily_log_returns(weights: dict, prices: pd.DataFrame) -> pd.Series:
    """Daily log returns of the portfolio kept at its target weights."""
    tick = [t for t in weights if t in prices.columns]
    w = pd.Series({t: weights[t] for t in tick})
    w = w / w.sum()
    simple = prices[tick].pct_change().dropna()
    return np.log1p(simple @ w)


def project_goal(weights: dict, prices: pd.DataFrame, capital: float, goal_amount: float,
                 years: float, monthly_contribution: float = 0.0,
                 expected_return: float | None = None, annual_vol: float | None = None,
                 method: str = "bootstrap", n_sims: int = 10_000, inflation: float = 0.0,
                 seed: int | None = 42) -> dict:
    """
    expected_return : yearly expected return (decimal) - pass the optimizer's
                      `exp_return`. None = use the historical average as is.
    annual_vol      : yearly volatility for the "normal" method (e.g. the risk
                      model's forecast). None = historical volatility.
    """
    if years <= 0 or capital < 0 or goal_amount <= 0:
        raise ValueError("years and goal_amount must be positive, capital non-negative.")
    months = max(1, int(round(years * 12)))
    rng = np.random.default_rng(seed)

    r = portfolio_daily_log_returns(weights, prices)
    if len(r) < BLOCK * 6:
        raise ValueError("Not enough price history for a simulation.")
    daily_var = float(r.var())

    if expected_return is not None:
        # log drift that gives this arithmetic expected return
        target = math.log1p(expected_return) / TRADING_DAYS - daily_var / 2
        r = r - r.mean() + target
    drift_source = "optimizer expected return" if expected_return is not None else "historical average"

    if method == "bootstrap":
        monthly_pool = r.rolling(BLOCK).sum().dropna().values     # every real 21-day stretch
        if expected_return is not None:                            # overlapping windows under-count the first and last weeks,
            monthly_pool = monthly_pool - monthly_pool.mean() + BLOCK * target   # so re-centre on the intended drift    
        sims = monthly_pool[rng.integers(0, len(monthly_pool), size=(n_sims, months))]
    elif method == "normal":
        m_mean = float(r.mean()) * BLOCK
        vol_d = (annual_vol / math.sqrt(TRADING_DAYS)) if annual_vol else math.sqrt(daily_var)
        if annual_vol and expected_return is not None:
            m_mean = (math.log1p(expected_return) / TRADING_DAYS - vol_d ** 2 / 2) * BLOCK
        sims = rng.normal(m_mean, vol_d * math.sqrt(BLOCK), size=(n_sims, months))
    else:
        raise ValueError("method must be 'bootstrap' or 'normal'")

    # month-by-month growth, top-up added at the end of each month
    value = np.full(n_sims, float(capital))
    paths = np.empty((n_sims, months))
    growth = np.exp(sims)
    for m in range(months):
        value = value * growth[:, m] + monthly_contribution
        paths[:, m] = value

    goal = goal_amount * (1 + inflation) ** years
    final = paths[:, -1]
    invested = capital + monthly_contribution * months
    pct = lambda a, q: float(np.percentile(a, q))

    fan = []
    for yr in range(1, int(math.ceil(months / 12)) + 1):
        col = min(yr * 12, months) - 1
        fan.append({"year": round((col + 1) / 12, 2),
                    **{f"p{q}": round(pct(paths[:, col], q), 0) for q in (5, 25, 50, 75, 95)}})

    failed = final[final < goal]
    return {
        "method": method,
        "drift_source": drift_source,
        "simulations": n_sims,
        "years": years,
        "goal_amount": round(goal, 2),
        "goal_in_todays_money": goal_amount if inflation else None,
        "total_invested": round(invested, 2),
        "probability_of_goal": round(float((final >= goal).mean()), 4),
        "probability_of_loss": round(float((final < invested).mean()), 4),
        "final_value": {f"p{q}": round(pct(final, q), 0) for q in (5, 25, 50, 75, 95)},
        "median_shortfall_if_missed": round(float(np.median(goal - failed)), 0) if len(failed) else 0,
        "fan_chart": fan,
    }


def required_monthly_contribution(weights, prices, capital, goal_amount, years,
                                  target_probability=0.75, expected_return=None,
                                  max_monthly=None, n_sims=5_000) -> float | None:
    """
    Smallest monthly top-up that reaches the goal with the target probability
    (binary search, same random draws each time). None if not reachable.
    """
    hi = max_monthly or max(goal_amount / max(1, years * 12), 1.0) * 2
    lo = 0.0
    run = lambda c: project_goal(weights, prices, capital, goal_amount, years, c,
                                 expected_return, n_sims=n_sims, seed=7)["probability_of_goal"]
    if run(lo) >= target_probability:
        return 0.0
    if run(hi) < target_probability:
        return None
    for _ in range(25):
        mid = (lo + hi) / 2
        if run(mid) >= target_probability:
            hi = mid
        else:
            lo = mid
    return round(hi, -2)      # rounded to the nearest 100 rupees
