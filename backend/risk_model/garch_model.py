"""
FinSight AI - risk model core: GJR-GARCH(1,1) with Student-t errors.

Model (r = daily log return in %):
    r(t)   = mu + e(t),           e(t) = sigma(t) * z(t),   z ~ Student-t(nu)
    s2(t)  = omega + (alpha + gamma * I[e(t-1) < 0]) * e(t-1)^2 + beta * s2(t-1)

    alpha : reaction to yesterday's shock
    gamma : EXTRA reaction when the shock was bad news (leverage effect)
    beta  : how long volatility stays high
    nu    : tail thickness (lower = more extreme crash days)

"Training" = estimating these 6 numbers per stock (maximum likelihood).
They are saved to a small JSON file. "Using" the model = loading the numbers,
running them over the latest returns, and forecasting forward.
"""

import json
import math
import os
from datetime import datetime

import numpy as np
import pandas as pd
from arch import arch_model
from scipy import stats

TRADING_DAYS = 252
HORIZON = 21                 # forecast horizon in trading days (~1 month)
SCALE = 100.0                # returns are modelled in percent (better for the optimizer)
MODEL_NAME = "GJR-GARCH(1,1), Student-t"
PARAM_NAMES = ["mu", "omega", "alpha[1]", "gamma[1]", "beta[1]", "nu"]


# ---------------------------------------------------------------------------
# returns
# ---------------------------------------------------------------------------
def to_log_returns(close: pd.Series) -> pd.Series:
    """Daily log returns in percent."""
    return (np.log(close).diff() * SCALE).dropna()


# ---------------------------------------------------------------------------
# model
# ---------------------------------------------------------------------------
def build_model(r: pd.Series):
    """GJR-GARCH(1,1): p=1 (alpha), o=1 (gamma, asymmetry), q=1 (beta)."""
    return arch_model(r, mean="Constant", vol="GARCH", p=1, o=1, q=1,
                      dist="t", rescale=False)


def fit(r: pd.Series):
    """Estimate the parameters on a return series. Returns the arch result."""
    r = r.dropna()
    return build_model(r).fit(disp="off", show_warning=False,
                              options={"maxiter": 1000})


def make_record(res, ticker: str, r: pd.Series) -> dict:
    """Turn a fitted result into a small, JSON-friendly record."""
    p = res.params
    alpha, gamma, beta = float(p["alpha[1]"]), float(p["gamma[1]"]), float(p["beta[1]"])
    omega, nu = float(p["omega"]), float(p["nu"])
    persistence = alpha + gamma / 2 + beta          # < 1 means volatility mean-reverts
    converged = int(res.convergence_flag) == 0
    ok = converged and persistence < 0.9999 and nu > 2.05 and omega > 0
    long_run_var = omega / (1 - persistence) if persistence < 1 else float("nan")
    return {
        "ticker": ticker,
        "params": {k: float(p[k]) for k in PARAM_NAMES},
        "persistence": persistence,
        "half_life_days": (math.log(0.5) / math.log(persistence)
                           if 0 < persistence < 1 else None),
        "long_run_vol_annual": (math.sqrt(long_run_var * TRADING_DAYS) / SCALE
                                if long_run_var == long_run_var else None),
        "loglik": float(res.loglikelihood),
        "n_obs": int(res.nobs),
        "train_start": str(r.index[0].date()),
        "train_end": str(r.index[-1].date()),
        "converged": converged,
        "ok": bool(ok),
    }


def fixed_result(r: pd.Series, params: dict):
    """Apply SAVED parameters to a return series (no re-estimation)."""
    model = build_model(r.dropna())
    return model.fix(pd.Series({k: params[k] for k in PARAM_NAMES}))


# ---------------------------------------------------------------------------
# Student-t helpers (standardized to unit variance)
# ---------------------------------------------------------------------------
def t_quantile_es(alpha: float, nu: float) -> tuple[float, float]:
    """
    For a unit-variance Student-t with nu degrees of freedom, return
    (alpha-quantile, expected value below that quantile). Both are negative.
    Used for VaR (quantile) and CVaR / Expected Shortfall (tail average).
    """
    ta = stats.t.ppf(alpha, nu)
    scale = math.sqrt((nu - 2) / nu)
    q = ta * scale
    es = -(stats.t.pdf(ta, nu) / alpha) * (nu + ta ** 2) / (nu - 1) * scale
    return q, es


# ---------------------------------------------------------------------------
# forecasting
# ---------------------------------------------------------------------------
def forecast(r: pd.Series, record: dict, horizon: int = HORIZON,
             alpha: float = 0.05) -> dict:
    """
    Forecast risk from the end of the return series using saved parameters.
    All outputs are in decimals (0.02 = 2%). VaR/CVaR are positive LOSS numbers.
    """
    params = record["params"]
    res = fixed_result(r, params)
    f = res.forecast(horizon=horizon, reindex=False)
    var_path = f.variance.values[-1]                       # daily variances, %^2

    mu = params["mu"]
    nu = params["nu"]
    s1 = math.sqrt(var_path[0])                            # next-day vol, %
    s_h = math.sqrt(var_path.sum())                        # total vol over horizon, %
    q, es = t_quantile_es(alpha, nu)
    z = stats.norm.ppf(alpha)                              # multi-day sums ~ normal

    return {
        "as_of": str(r.index[-1].date()),
        "vol_1d": s1 / SCALE,
        "vol_horizon": s_h / SCALE,
        "vol_annual": math.sqrt(var_path.mean() * TRADING_DAYS) / SCALE,
        "long_run_vol_annual": record.get("long_run_vol_annual"),
        f"var_{int((1 - alpha) * 100)}_1d": -(mu + s1 * q) / SCALE,
        f"cvar_{int((1 - alpha) * 100)}_1d": -(mu + s1 * es) / SCALE,
        f"var_{int((1 - alpha) * 100)}_{horizon}d": -(mu * horizon + s_h * z) / SCALE,
        "horizon_days": horizon,
        "variance_path_daily": [v / SCALE ** 2 for v in var_path],
    }


# ---------------------------------------------------------------------------
# save / load
# ---------------------------------------------------------------------------
def save_params(records: dict, path: str, meta: dict):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    payload = {
        "model": MODEL_NAME,
        "created": datetime.now().isoformat(timespec="seconds"),
        "meta": meta,
        "models": records,
    }
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=2)


def load_params(path: str) -> dict:
    with open(path) as fh:
        return json.load(fh)
