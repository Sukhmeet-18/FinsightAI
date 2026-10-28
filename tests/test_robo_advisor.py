"""
Automated tests for the robo-advisor. They build a small fake market in memory,
so they run anywhere, without the real data.

Run from the project root:
    pip install pytest
    python -m pytest tests
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import pytest

from backend.robo_advisor.metrics import historical_metrics, max_drawdown, portfolio_value
from backend.robo_advisor.monte_carlo import project_goal
from backend.robo_advisor.optimizer import PROFILES, build_portfolio
from backend.robo_advisor.risk_profile import score_risk_profile
from backend.robo_advisor.stress_test import run_stress_tests


@pytest.fixture(scope="module")
def market():
    rng = np.random.default_rng(0)
    dates = pd.bdate_range("2007-01-01", "2026-06-30")
    n = len(dates)
    mkt = rng.normal(0.0005, 0.011, n)
    bench = pd.Series(10000 * np.exp(np.cumsum(mkt)), index=dates)
    cap_of, cols = {}, {}
    for tier, k, vol, beta in (("large", 12, 0.009, 0.9), ("mid", 12, 0.013, 1.1), ("small", 12, 0.018, 1.3)):
        for i in range(k):
            t = f"{tier[0].upper()}{i}"
            cap_of[t] = tier
            r = beta * mkt + rng.normal(0.0002, vol, n)
            cols[t] = 100 * np.exp(np.cumsum(r))
    full = pd.DataFrame(cols, index=dates)
    full.loc[:"2015-12-31", "S11"] = np.nan          # listed later
    window = full.loc["2023-07-01":].dropna(axis=1)
    return full, window, bench, cap_of


# ---------------- risk profile ----------------
@pytest.mark.parametrize("answers, expected", [([1, 1, 1, 1, 1], "conservative"),
                                               ([3, 3, 3, 3, 3], "balanced"),
                                               ([4, 4, 4, 4, 4], "aggressive")])
def test_profile_scoring(answers, expected):
    assert score_risk_profile(answers)[0] == expected


@pytest.mark.parametrize("bad", [[1, 2, 3], [0, 1, 1, 1, 1], [5, 1, 1, 1, 1]])
def test_profile_rejects_bad_answers(bad):
    with pytest.raises(ValueError):
        score_risk_profile(bad)


# ---------------- optimizer ----------------
@pytest.mark.parametrize("profile", list(PROFILES))
def test_portfolio_rules(market, profile):
    _, window, bench, cap_of = market
    b = bench.reindex(window.index)
    res = build_portfolio(window, cap_of, profile, 500_000, benchmark=b)
    weights = [a["weight"] for a in res["allocation"]]
    cfg = PROFILES[profile]

    assert abs(sum(weights) - 1) < 1e-3                         # fully invested
    assert all(w >= 0 for w in weights)                         # no short selling
    assert max(weights) <= cfg["max_weight"] + 1e-3             # per-stock limit
    for tier, cap in cfg["cap_upper"].items():                  # cap-tier ceilings
        assert res["cap_split"].get(tier, 0) <= cap + 1e-3
    for tier, low in cfg["cap_lower"].items():                  # cap-tier floors
        assert res["cap_split"].get(tier, 0) >= low - 1e-3
    assert sum(a["amount"] for a in res["allocation"]) == pytest.approx(500_000, rel=1e-3)


def test_risk_ladder(market):
    """More aggressive profiles should take at least as much risk."""
    _, window, bench, cap_of = market
    b = bench.reindex(window.index)
    vols = [build_portfolio(window, cap_of, p, 1, benchmark=b)["metrics"]["volatility"]
            for p in ("conservative", "balanced", "aggressive")]
    assert vols[0] <= vols[1] + 1e-3 <= vols[2] + 2e-3


# ---------------- metrics ----------------
def test_max_drawdown_simple():
    v = pd.Series([100, 120, 90, 130], index=pd.bdate_range("2024-01-01", periods=4))
    assert max_drawdown(v)["max_drawdown"] == pytest.approx(-0.25)


def test_portfolio_value_starts_at_one(market):
    _, window, _, _ = market
    w = {window.columns[0]: 0.5, window.columns[1]: 0.5}
    assert portfolio_value(w, window).iloc[0] == pytest.approx(1.0)


def test_historical_metrics_fields(market):
    _, window, bench, _ = market
    w = {window.columns[0]: 0.5, window.columns[1]: 0.5}
    h = historical_metrics(w, window, bench.reindex(window.index))
    assert h["max_drawdown"] <= 0 and h["volatility"] > 0 and "beta" in h


# ---------------- stress test ----------------
def test_stress_test_handles_missing_history(market):
    full, _, bench, _ = market
    w = {"S11": 0.9, "L0": 0.1}                    # S11 did not exist in 2008
    res = {r["event"]: r for r in run_stress_tests(w, full[list(w)], bench)}
    assert res["Global Financial Crisis"]["status"] != "ok"
    assert res["COVID-19 crash"]["status"] == "ok"


# ---------------- Monte Carlo ----------------
def test_monte_carlo_outputs(market):
    _, window, _, _ = market
    w = {window.columns[0]: 0.5, window.columns[1]: 0.5}
    g = project_goal(w, window, 100_000, 200_000, 5, 2_000, expected_return=0.12, n_sims=2_000)
    assert 0 <= g["probability_of_goal"] <= 1
    fv = g["final_value"]
    assert fv["p5"] <= fv["p50"] <= fv["p95"]
    assert g["total_invested"] == 100_000 + 2_000 * 60


def test_more_saving_never_lowers_the_chance(market):
    _, window, _, _ = market
    w = {window.columns[0]: 0.5, window.columns[1]: 0.5}
    lo = project_goal(w, window, 100_000, 300_000, 5, 0, expected_return=0.1, n_sims=3_000)
    hi = project_goal(w, window, 100_000, 300_000, 5, 3_000, expected_return=0.1, n_sims=3_000)
    assert hi["probability_of_goal"] >= lo["probability_of_goal"]
