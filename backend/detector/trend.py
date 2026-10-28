"""What the numbers show: the direction of growth, margin and return on equity from the yearly results."""
import math

import pandas as pd

# How big a move counts as 'clearly up' or 'clearly down' (about +0.76 on the -1..+1 scale)
GROWTH_SCALE, MARGIN_SCALE, ROE_SCALE = 0.10, 0.02, 0.03


def trend_from_dataset(ticker, csv_path):
    df = pd.read_csv(csv_path)
    df["ticker"] = df["ticker"].astype(str).str.replace(".NS", "", regex=False).str.upper()
    df["period"] = pd.to_datetime(df["period"])
    d = df[(df["ticker"] == ticker.upper().replace(".NS", "")) & (df["period"].dt.month == 3)].sort_values("period")
    if d.empty:
        return None

    def last(col):
        s = d[col].dropna()
        return float(s.iloc[-1]) if len(s) else None

    def change(col):
        s = d[col].dropna()
        return float(s.iloc[-1] - s.iloc[0]) if len(s) >= 2 else None

    comp = {"revenue_growth_latest": last("revenue_growth"), "margin_change": change("profit_margin"), "roe_change": change("roe"),
            "years": [p.strftime("%Y") for p in d["period"]]}
    parts = []
    if comp["revenue_growth_latest"] is not None:
        parts.append(math.tanh(comp["revenue_growth_latest"] / GROWTH_SCALE))
    if comp["margin_change"] is not None:
        parts.append(math.tanh(comp["margin_change"] / MARGIN_SCALE))
    if comp["roe_change"] is not None:
        parts.append(math.tanh(comp["roe_change"] / ROE_SCALE))
    comp["score"] = sum(parts) / len(parts) if len(parts) >= 2 else None       # needs at least two of the three signals
    comp["signals_used"] = len(parts)
    return comp
