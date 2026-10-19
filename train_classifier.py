import pandas as pd

d = pd.read_csv("data/ml_dataset.csv", parse_dates=["period"])
d = d[d["period"].dt.month == 3].copy()          # keep March year-ends so every stock is judged over the same window
d["year"] = d["period"].dt.year

FEATS = ["revenue_growth", "profit_margin", "roe"]
for f in FEATS:
    d[f + "_rk"] = d.groupby("year")[f].rank(pct=True)     # rank vs other companies the same year (0 to 1)
    d[f + "_na"] = d[f].isna().astype(int)                 # was the number missing?
    d[f + "_rk"] = d[f + "_rk"].fillna(0.5)                # missing = middle of the pack
X_COLS = [f + s for f in FEATS for s in ("_rk", "_na")]
print(len(d), "rows kept |", len(X_COLS), "features:", X_COLS)

FOLDS = [(2023, 2024), (2024, 2025)]                       # (last training year, test year)
for last, test in FOLDS:
    tr, te = d[d.year <= last], d[d.year == test]
    print(f"train to FY{last}: {len(tr)} rows | test FY{test}: {len(te)} rows | "
          f"always-yes on test: {te.label_beats_market.mean():.1%}")


    # ---------------- Step 3: three models, fixed settings (no tuning on the test years) ----------------
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

MODELS = {
    "Logistic regression": lambda: LogisticRegression(max_iter=1000),
    "Random forest": lambda: RandomForestClassifier(n_estimators=300, max_depth=4, min_samples_leaf=10, random_state=7),
    "Gradient boosting": lambda: HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150, min_samples_leaf=15, random_state=7),
}

def scores(y, p):
    yhat = (p >= 0.5).astype(int)
    return {"acc": accuracy_score(y, yhat), "prec": precision_score(y, yhat, zero_division=0),
            "rec": recall_score(y, yhat), "f1": f1_score(y, yhat), "auc": roc_auc_score(y, p)}

rng = np.random.default_rng(7)
def mean_auc_range(parts, n=1000):
    v = []
    for _ in range(n):
        a = []
        for y, p in parts:
            i = rng.integers(0, len(y), len(y))
            if len(set(y[i])) == 2:
                a.append(roc_auc_score(y[i], p[i]))
        if len(a) == len(parts):
            v.append(np.mean(a))
    return np.percentile(v, [2.5, 97.5])

rows, parts = [], {k: [] for k in MODELS}
for last, test in FOLDS:
    tr, te = d[d.year <= last], d[d.year == test]
    y = te.label_beats_market.values
    rows.append({"model": "Always yes (baseline)", "test": f"FY{test}", "acc": y.mean(), "prec": y.mean(), "rec": 1.0,
                 "f1": 2 * y.mean() / (1 + y.mean()), "auc": 0.5})
    for name, make in MODELS.items():
        m = make().fit(tr[X_COLS], tr.label_beats_market)
        p = m.predict_proba(te[X_COLS])[:, 1]
        rows.append({"model": name, "test": f"FY{test}", **scores(y, p)})
        parts[name].append((y, p))

for name, ps in parts.items():
    y, p = np.concatenate([a for a, _ in ps]), np.concatenate([b for _, b in ps])
    r = scores(y, p)
    r["auc"] = np.mean([roc_auc_score(a, b) for a, b in ps])     # average of each year's own AUC
    lo, hi = mean_auc_range(ps)
    rows.append({"model": name, "test": "both years", **r, "auc_95%": f"{lo:.2f}-{hi:.2f}"})

pd.set_option("display.width", 200)
print()
print(pd.DataFrame(rows).round(3).fillna("").to_string(index=False))


# ---------------- Step 4: would buying the model's top third have beaten the market? ----------------
from scipy.stats import spearmanr
COST = 0.002          # 0.2% to buy and later sell, once a year

out = []
for name, make in MODELS.items():
    net_g = all_g = nifty_g = 1.0
    for last, test in FOLDS:
        tr, te = d[d.year <= last], d[d.year == test].copy()
        te["p"] = make().fit(tr[X_COLS], tr.label_beats_market).predict_proba(te[X_COLS])[:, 1]
        top = te[te.p >= te.p.quantile(2 / 3)]
        bottom = te[te.p <= te.p.quantile(1 / 3)]
        net = top.fwd_return.mean() - COST
        nifty = te.bench_fwd_return.iloc[0]
        net_g *= 1 + net; all_g *= 1 + te.fwd_return.mean(); nifty_g *= 1 + nifty
        out.append({"model": name, "test": f"FY{test}", "top third": net, "all stocks": te.fwd_return.mean(),
                    "Nifty": nifty, "bottom third": bottom.fwd_return.mean(),
                    "hit rate": (top.fwd_return > top.bench_fwd_return).mean(),
                    "rank corr": spearmanr(te.p, te.fwd_return)[0]})
    out.append({"model": name, "test": "2 yrs compounded", "top third": net_g - 1, "all stocks": all_g - 1, "Nifty": nifty_g - 1})

print()
print("Returns are for holding each year's picks for one year, after a 0.2% cost.")
print(pd.DataFrame(out).round(3).fillna("").to_string(index=False))


# ---------------- Step 5 (extension): add price momentum, volatility and company size ----------------
import os

PX = {}
for t in d.ticker.unique():
    f = os.path.join("data", "prices", t + ".csv")
    if os.path.exists(f):
        PX[t] = pd.read_csv(f, index_col=0, parse_dates=True)["Close"]

def last_price(s, date):
    s = s.loc[:date]
    return s.iloc[-1] if len(s) else np.nan

mom, vol = [], []
for r in d.itertuples():
    s = PX.get(r.ticker)
    buy = r.period + pd.Timedelta(days=90)                      # the day we would buy
    if s is None or len(s.loc[:buy]) < 250:
        mom.append(np.nan); vol.append(np.nan); continue
    mom.append(last_price(s, buy - pd.Timedelta(days=30)) / last_price(s, buy - pd.Timedelta(days=365)) - 1)   # 12-month move, skipping the last month
    vol.append(s.loc[buy - pd.Timedelta(days=365):buy].pct_change().std() * np.sqrt(252))                      # past-year volatility
d["momentum"], d["volatility"] = mom, vol

for f in ["momentum", "volatility"]:
    d[f + "_rk"] = d.groupby("year")[f].rank(pct=True)
    d[f + "_na"] = d[f].isna().astype(int)
    d[f + "_rk"] = d[f + "_rk"].fillna(0.5)
d["size_ord"] = d["cap_category"].map({"small": 0, "mid": 1, "large": 2})
X2_COLS = X_COLS + ["momentum_rk", "momentum_na", "volatility_rk", "volatility_na", "size_ord"]
print("\nprice features missing for", int(d.momentum_na.sum()), "of", len(d), "rows")

def report(cols, title):
    rows = []
    for name, make in MODELS.items():
        g_top = g_all = 1.0
        for last, test in FOLDS:
            tr, te = d[d.year <= last], d[d.year == test].copy()
            te["p"] = make().fit(tr[cols], tr.label_beats_market).predict_proba(te[cols])[:, 1]
            top = te[te.p >= te.p.quantile(2 / 3)]
            g_top *= 1 + top.fwd_return.mean() - COST; g_all *= 1 + te.fwd_return.mean()
            rows.append({"model": name, "test": f"FY{test}", "AUC": roc_auc_score(te.label_beats_market, te.p),
                         "top third": top.fwd_return.mean() - COST, "all stocks": te.fwd_return.mean(),
                         "rank corr": spearmanr(te.p, te.fwd_return)[0]})
        rows.append({"model": name, "test": "2 yrs", "AUC": np.mean([x["AUC"] for x in rows[-2:]]),
                     "top third": g_top - 1, "all stocks": g_all - 1})
    print("\n" + title)
    print(pd.DataFrame(rows).round(3).fillna("").to_string(index=False))

report(X_COLS, "A) fundamentals only (the synopsis model)")
report(X2_COLS, "B) fundamentals + momentum, volatility, size (extension)")


# ---------------- Step 6: train the final model on all rows and score today's companies ----------------
import os
import joblib

final = LogisticRegression(max_iter=1000).fit(d[X_COLS], d.label_beats_market)
print("\nWhat the final model learned (positive = pushes the score up):")
for c, w in sorted(zip(X_COLS, final.coef_[0]), key=lambda x: -abs(x[1])):
    print(f"  {c:20s} {w:+.2f}")

# today's group: the latest annual numbers of every company in the 150-stock universe
m = pd.read_csv("data/metrics_latest.csv")
for f in FEATS:
    m[f + "_rk"] = m[f].rank(pct=True)
    m[f + "_na"] = m[f].isna().astype(int)
    m[f + "_rk"] = m[f + "_rk"].fillna(0.5)
m["p"] = final.predict_proba(m[X_COLS])[:, 1]
lo, hi = m.p.quantile([1 / 3, 2 / 3])                      # top third = Buy, bottom third = Sell
m["label"] = np.where(m.p >= hi, "Buy", np.where(m.p <= lo, "Sell", "Hold"))
print("\ncompanies scored:", len(m), "| Buy:", (m.label == "Buy").sum(), "Hold:", (m.label == "Hold").sum(), "Sell:", (m.label == "Sell").sum())
FIVE = ["RELIANCE", "TCS", "HINDUNILVR", "MARUTI", "ITC"]
print(m[m.ticker.isin(FIVE)][["ticker", "revenue_growth", "profit_margin", "roe", "p", "label"]].round(3).to_string(index=False))

os.makedirs("models/classifier", exist_ok=True)
joblib.dump({"model": final, "cols": X_COLS}, "models/classifier/logreg.joblib")
print("\nsaved models/classifier/logreg.joblib")