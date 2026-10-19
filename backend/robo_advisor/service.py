"""
RoboAdvisor - the single entry point the API (and the dashboard) uses.

    robo = RoboAdvisor()                       # loads data + risk model once
    robo.recommend(capital=500000, risk_answers=[3,3,2,3,3],
                   goal_amount=1500000, years=7, monthly_contribution=5000)

Returns one dict with everything the dashboard needs:
    profile -> allocation -> expected metrics -> forward risk (GJR-GARCH)
    -> past track record -> stress tests -> goal projection -> frontier chart
"""

from backend.common.data_loader import (load_benchmark, load_close_table, load_universe,
                                        window_prices)
from .metrics import growth_series, historical_metrics
from .monte_carlo import project_goal, required_monthly_contribution
from .optimizer import (RISK_FREE_RATE, build_portfolio, estimate_inputs, frontier_points,
                        select_candidates)
from .risk_profile import QUESTIONS, score_risk_profile
from .stress_test import run_stress_tests

CORE = ["RELIANCE", "TCS", "ITC", "MARUTI", "HINDUNILVR"]
LOOKBACK_YEARS = 3
DISCLAIMER = ("FinSight AI is an educational project, not investment advice. "
              "Past performance and model forecasts do not guarantee future results.")


class RoboAdvisor:
    def __init__(self, use_risk_model: bool = True):
        self.use_risk_model = use_risk_model
        self.reload()

    def reload(self):
        """(Re)load data and models - call after the data is refreshed."""
        self.cap_of = load_universe()
        self.table = load_close_table(list(self.cap_of))            # full history
        self.benchmark_full = load_benchmark()
        self.prices = window_prices(self.table, lookback_years=LOOKBACK_YEARS)
        self.benchmark = self.benchmark_full.reindex(self.prices.index).ffill().bfill()
        self.risk_model, self.risk_model_note = None, "risk model not used"
        if self.use_risk_model:
            try:
                from backend.risk_model.service import RiskModel
                self.risk_model = RiskModel()
                self.risk_model_note = f"GJR-GARCH loaded from {self.risk_model.path}"
            except Exception as e:                                   # app still works without it
                self.risk_model_note = f"risk model unavailable ({e}); using historical covariance"

    @staticmethod
    def questions():
        return QUESTIONS

    def recommend(self, capital: float, risk_answers: list[int] | None = None,
                  profile: str | None = None, goal_amount: float | None = None,
                  years: float | None = None, monthly_contribution: float = 0.0,
                  inflation: float = 0.0, include_frontier: bool = True) -> dict:
        if capital <= 0:
            raise ValueError("capital must be positive")
        score = None
        if profile is None:
            if risk_answers is None:
                raise ValueError("give either risk_answers or profile")
            profile, score = score_risk_profile(risk_answers)

        core = [t for t in CORE if t in self.prices.columns]
        result = build_portfolio(self.prices, self.cap_of, profile, capital,
                                 benchmark=self.benchmark, always_include=core,
                                 risk_model=self.risk_model)
        weights = {a["ticker"]: a["weight"] for a in result["allocation"]}
        result["risk_score"] = score
        result["risk_model"] = self.risk_model_note

        # past track record of these weights
        result["historical"] = historical_metrics(weights, self.prices[list(weights)],
                                                  self.benchmark, RISK_FREE_RATE, capital)
        result["growth_chart"] = growth_series(weights, self.prices[list(weights)], self.benchmark)

        # crash replays
        result["stress_test"] = run_stress_tests(weights, self.table[list(weights)],
                                                 self.benchmark_full, capital)

        # goal projection
        if goal_amount and years:
            gp = project_goal(weights, self.prices, capital, goal_amount, years,
                              monthly_contribution, expected_return=result["metrics"]["exp_return"],
                              inflation=inflation)
            gp["monthly_needed_for_75pct"] = required_monthly_contribution(
                weights, self.prices, capital, gp["goal_amount"], years, 0.75,
                expected_return=result["metrics"]["exp_return"])
            result["goal_projection"] = gp

        # efficient frontier + where this portfolio sits on it
        if include_frontier:
            cands = select_candidates(self.prices, self.cap_of, always_include=core)
            mu, S, _ = estimate_inputs(self.prices[cands], self.benchmark,
                                       risk_model=self.risk_model)
            result["frontier"] = {
                "points": frontier_points(mu, S, self.cap_of, profile, n_points=15),
                "portfolio": {"volatility": result["metrics"]["volatility"],
                              "return": result["metrics"]["exp_return"]},
            }

        result["disclaimer"] = DISCLAIMER
        return result
