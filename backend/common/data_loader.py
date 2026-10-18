"""
Shared data loader - reads the CSVs made by the data fetch script.
Used by the robo-advisor and the risk model.

Expected layout (project root):
    data/universe.csv            symbol, cap_category
    data/prices/<SYMBOL>.csv     yfinance history (Date index, Close column)
    data/benchmark_NIFTY50.csv   Nifty 50 history

Set the env variable FINSIGHT_DATA_DIR to point somewhere else if needed.
"""

import os
import pandas as pd

DATA_DIR = os.environ.get("FINSIGHT_DATA_DIR", "data")
TRADING_DAYS = 252


def read_close(path: str) -> pd.Series:
    """Read one yfinance CSV and return a clean, tz-naive Close series."""
    df = pd.read_csv(path, index_col=0)
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)
    idx = pd.to_datetime(df.index, utc=True).tz_convert(None).normalize()
    s = pd.Series(pd.to_numeric(df["Close"], errors="coerce").values, index=idx, dtype=float)
    s = s[s > 0]
    return s[~s.index.duplicated(keep="last")].sort_index()


def load_universe(data_dir: str = DATA_DIR) -> dict:
    """Return {symbol: cap_category} for the frozen universe."""
    u = pd.read_csv(os.path.join(data_dir, "universe.csv"))
    return dict(zip(u["symbol"], u["cap_category"]))


def load_prices(tickers=None, data_dir: str = DATA_DIR, end=None,
                lookback_years: float = 3.0, max_missing: float = 0.05) -> pd.DataFrame:
    """
    Clean price table (dates x tickers) for the lookback window.
    - end            : last date to use (None = latest). Set this for backtests.
    - lookback_years : history used to estimate returns/risk.
    - max_missing    : drop a stock if more than this share of days is missing.
    """
    prices_dir = os.path.join(data_dir, "prices")
    if tickers is None:
        tickers = [f[:-4] for f in os.listdir(prices_dir) if f.endswith(".csv")]

    series = {}
    for t in tickers:
        path = os.path.join(prices_dir, f"{t}.csv")
        if os.path.exists(path):
            s = read_close(path)
            if not s.empty:
                series[t] = s
    if not series:
        raise ValueError("No price files found - run the data fetch script first.")

    prices = pd.DataFrame(series).sort_index()
    end_ts = pd.Timestamp(end) if end is not None else prices.index.max()
    start_ts = end_ts - pd.DateOffset(years=lookback_years)
    prices = prices.loc[(prices.index > start_ts) & (prices.index <= end_ts)]

    coverage = prices.notna().mean()
    prices = prices.loc[:, coverage >= (1 - max_missing)]
    prices = prices.ffill(limit=5).dropna()
    return prices


def load_benchmark(data_dir: str = DATA_DIR, index=None) -> pd.Series:
    """Nifty 50 Close series, optionally aligned to a given date index."""
    s = read_close(os.path.join(data_dir, "benchmark_NIFTY50.csv"))
    s.name = "NIFTY50"
    if index is not None:
        s = s.reindex(index).ffill().bfill()
    return s
