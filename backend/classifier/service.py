import os

import joblib
import numpy as np
import pandas as pd

MODEL_PATH = os.path.join("models", "classifier", "logreg.joblib")
METRICS_PATH = os.path.join("data", "metrics_latest.csv")
FEATS = ["revenue_growth", "profit_margin", "roe"]
NAMES = {"revenue_growth": "Revenue growth", "profit_margin": "Profit margin", "roe": "Return on equity"}
_state = {}


def _load():
    if _state:
        return _state
    bundle = joblib.load(MODEL_PATH)
    m = pd.read_csv(METRICS_PATH)
    for f in FEATS:                                  # same steps as in training
        m[f + "_rk"] = m[f].rank(pct=True)
        m[f + "_na"] = m[f].isna().astype(int)
        m[f + "_rk"] = m[f + "_rk"].fillna(0.5)
    m["p"] = bundle["model"].predict_proba(m[bundle["cols"]])[:, 1]
    lo, hi = m.p.quantile([1 / 3, 2 / 3])            # top third = Buy, bottom third = Sell
    m["label"] = np.where(m.p >= hi, "Buy", np.where(m.p <= lo, "Sell", "Hold"))
    _state.update(bundle=bundle, m=m.set_index("ticker"))
    return _state


def model_view(ticker):
    """Experimental learned view of one company (ticker without .NS), or None if unavailable."""
    try:
        s = _load()
        m, bundle = s["m"], s["bundle"]
        if ticker not in m.index:
            return None
        r = m.loc[ticker]
        coef = dict(zip(bundle["cols"], bundle["model"].coef_[0]))
        drivers = sorted(
            [{"name": NAMES[f], "effect": round(float(coef[f + "_rk"] * (r[f + "_rk"] - 0.5)), 3)} for f in FEATS],
            key=lambda x: -abs(x["effect"]),
        )
        return {
            "label": str(r["label"]),
            "probability": round(float(r["p"]), 3),
            "rank": int((m.p > r["p"]).sum()) + 1,
            "of": int(len(m)),
            "drivers": drivers,
        }
    except Exception:
        return None