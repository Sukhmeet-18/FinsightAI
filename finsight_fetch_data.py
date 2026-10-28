

import os
import io
import time
import yfinance as yf
import pandas as pd
import requests

# ------------------------- config -------------------------
OUT = "data"
PRICES_DIR = os.path.join(OUT, "prices")
FUND_DIR = os.path.join(OUT, "fundamentals")
CORE = ["RELIANCE", "TCS", "ITC", "MARUTI", "HINDUNILVR"]  # forced into large cap
BENCHMARK = "^NSEI"                                         # Nifty 50
PRICE_PERIOD = "max"                                        # full history (portfolio + stress tests)
ML_YEARS = {2022, 2023, 2024, 2025}                        # fiscal years used for ML features
N_PER_TIER = 50
SLEEP = 1.0
FORCE_REFRESH = False        # True = re-download even if a file already exists
# ----------------------------------------------------------

for d in (OUT, PRICES_DIR, FUND_DIR):
    os.makedirs(d, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
INDEX_SOURCES = {
    "large": (["https://niftyindices.com/IndexConstituent/ind_nifty100list.csv",
               "https://archives.nseindia.com/content/indices/ind_nifty100list.csv"],
              "ind_nifty100list.csv"),
    "mid":   (["https://niftyindices.com/IndexConstituent/ind_niftymidcap150list.csv",
               "https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv"],
              "ind_niftymidcap150list.csv"),
    "small": (["https://niftyindices.com/IndexConstituent/ind_niftysmallcap250list.csv",
               "https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv"],
              "ind_niftysmallcap250list.csv"),
}
UNIVERSE_CSV = os.path.join(OUT, "universe.csv")


# ---------------------------------------------------------------------------
# 1. Universe - built once, then frozen in universe.csv so re-runs are stable
# ---------------------------------------------------------------------------
def read_symbol_list(urls, local_name):
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return [s.strip().upper() for s in pd.read_csv(io.StringIO(r.text))["Symbol"].tolist()]
        except Exception as e:
            print(f"    [warn] {url} -> {e}")
    if os.path.exists(local_name):
        print(f"    using local {local_name}")
        return [s.strip().upper() for s in pd.read_csv(local_name)["Symbol"].tolist()]
    print(f"    [error] could not get {local_name}; download it from niftyindices.com "
          f"and place it next to this script.")
    return []


def build_universe():
    if os.path.exists(UNIVERSE_CSV) and not FORCE_REFRESH:
        u = pd.read_csv(UNIVERSE_CSV)
        print(f"Using frozen universe from {UNIVERSE_CSV} ({len(u)} companies).")
        return dict(zip(u["symbol"], u["cap_category"]))
    print("Building universe (first run)...")
    lists = {t: read_symbol_list(urls, local) for t, (urls, local) in INDEX_SOURCES.items()}
    large = (list(CORE) + [s for s in lists["large"] if s not in CORE])[:N_PER_TIER]
    mid, small = lists["mid"][:N_PER_TIER], lists["small"][:N_PER_TIER]
    cap = {}
    for s in large: cap[s] = "large"
    for s in mid:   cap.setdefault(s, "mid")
    for s in small: cap.setdefault(s, "small")
    pd.DataFrame({"symbol": list(cap), "cap_category": list(cap.values())}).to_csv(UNIVERSE_CSV, index=False)
    print(f"  large {len(large)}  mid {len(mid)}  small {len(small)}  total {len(cap)}")
    return cap


cap_of = build_universe()
symbols = list(cap_of.keys())


# ---------------------------------------------------------------------------
# 2. Download phase - skips anything already on disk
# ---------------------------------------------------------------------------
def find_row(df, names):
    if df is None or df.empty:
        return None
    for n in names:
        if n in df.index:
            return df.loc[n]
    return None


def fetch_fundamentals(ticker):
    t = yf.Ticker(ticker)
    inc = t.income_stmt
    if inc is None or inc.empty:
        inc = t.financials
    bs = t.balance_sheet
    rev = find_row(inc, ["Total Revenue", "TotalRevenue", "Operating Revenue"])
    ni = find_row(inc, ["Net Income", "NetIncome", "Net Income Common Stockholders"])
    eq = find_row(bs, ["Stockholders Equity", "Total Stockholder Equity",
                       "Common Stock Equity", "Stockholders' Equity"])
    if rev is None or ni is None:
        return None
    df = pd.DataFrame({"revenue": rev, "net_income": ni})
    if eq is not None:
        df["equity"] = eq
    df = df.sort_index()
    df["profit_margin"] = df["net_income"] / df["revenue"]
    if "equity" in df.columns:
        df["roe"] = df["net_income"] / df["equity"]
    df["revenue_growth"] = df["revenue"].pct_change()
    df.index.name = "period"
    return df                       # FULL history saved; window applied later


# benchmark (cached)
bench_path = os.path.join(OUT, "benchmark_NIFTY50.csv")
if FORCE_REFRESH or not os.path.exists(bench_path):
    print("Fetching benchmark (Nifty 50)...")
    b = yf.Ticker(BENCHMARK).history(period=PRICE_PERIOD, auto_adjust=True)
    b.index = b.index.tz_localize(None)
    b.to_csv(bench_path)
else:
    print("Benchmark already cached - skipping.")

failures, downloaded, skipped = [], 0, 0
for i, sym in enumerate(symbols, 1):
    tk = sym + ".NS"
    price_path = os.path.join(PRICES_DIR, f"{sym}.csv")
    fund_path = os.path.join(FUND_DIR, f"{sym}.csv")
    need_price = FORCE_REFRESH or not os.path.exists(price_path)
    need_fund = FORCE_REFRESH or not os.path.exists(fund_path)
    if not need_price and not need_fund:
        skipped += 1
        continue
    print(f"[{i}/{len(symbols)}] {tk} ({cap_of[sym]})")
    try:
        if need_price:
            px = yf.Ticker(tk).history(period=PRICE_PERIOD, auto_adjust=True)
            if px.empty:
                raise ValueError("no price data")
            px.index = px.index.tz_localize(None)
            px.to_csv(price_path)
        if need_fund:
            f = fetch_fundamentals(tk)
            if f is not None and not f.empty:
                f.to_csv(fund_path)
            else:
                print(f"    [warn] no fundamentals for {tk}")
        downloaded += 1
        time.sleep(SLEEP)
    except Exception as e:
        print(f"    [fail] {tk}: {e}")
        failures.append(f"{tk}: {e}")
        time.sleep(SLEEP)

print(f"\nDownload phase: {downloaded} fetched, {skipped} already cached, {len(failures)} failed.")


# ---------------------------------------------------------------------------
# 3. Build phase - rebuild combined tables from EVERYTHING on disk
#    (so cached + newly fetched tickers are all included)
# ---------------------------------------------------------------------------
def price_on_or_after(px, date):
    s = px.loc[px.index >= date]
    return float(s["Close"].iloc[0]) if len(s) else None


print("Rebuilding metrics_latest.csv and ml_dataset.csv from cached files...")
bench = pd.read_csv(bench_path, index_col=0, parse_dates=True)

latest_rows, ml_rows = [], []
for sym in symbols:
    fund_path = os.path.join(FUND_DIR, f"{sym}.csv")
    price_path = os.path.join(PRICES_DIR, f"{sym}.csv")
    if not os.path.exists(fund_path):
        continue
    f = pd.read_csv(fund_path, index_col=0, parse_dates=True)
    fw = f[f.index.year.isin(ML_YEARS)]            # apply ML window here
    if fw.empty:
        continue
    last = fw.iloc[-1]
    latest_rows.append({
        "ticker": sym, "cap_category": cap_of.get(sym),
        "revenue": last.get("revenue"), "net_income": last.get("net_income"),
        "equity": last.get("equity"), "profit_margin": last.get("profit_margin"),
        "roe": last.get("roe"), "revenue_growth": last.get("revenue_growth"),
    })
    if not os.path.exists(price_path):
        continue
    px = pd.read_csv(price_path, index_col=0, parse_dates=True)
    for period_end in fw.index:
        p0 = price_on_or_after(px, period_end + pd.Timedelta(days=90))
        p1 = price_on_or_after(px, period_end + pd.Timedelta(days=455))
        b0 = price_on_or_after(bench, period_end + pd.Timedelta(days=90))
        b1 = price_on_or_after(bench, period_end + pd.Timedelta(days=455))
        if None in (p0, p1, b0, b1) or p0 == 0 or b0 == 0:
            continue
        r = fw.loc[period_end]
        ml_rows.append({
            "ticker": sym, "cap_category": cap_of.get(sym),
            "period": str(period_end.date()),
            "revenue_growth": r.get("revenue_growth"),
            "profit_margin": r.get("profit_margin"), "roe": r.get("roe"),
            "fwd_return": p1 / p0 - 1, "bench_fwd_return": b1 / b0 - 1,
            "label_beats_market": int((p1 / p0 - 1) > (b1 / b0 - 1)),
        })

if latest_rows:
    pd.DataFrame(latest_rows).to_csv(os.path.join(OUT, "metrics_latest.csv"), index=False)
if ml_rows:
    pd.DataFrame(ml_rows).to_csv(os.path.join(OUT, "ml_dataset.csv"), index=False)
if failures:
    with open(os.path.join(OUT, "failures.txt"), "w") as fh:
        fh.write("\n".join(failures))

print("\nDone.")
print(f"  Companies with metrics : {len(latest_rows)}")
print(f"  ML rows                : {len(ml_rows)}")
print(f"  Failures this run      : {len(failures)} (see data/failures.txt; re-run to retry)")
print(f"  Output folder          : {os.path.abspath(OUT)}")
