"""
Backtest the robo-advisor for all three profiles (your main evaluation result).

Pretends to start investing on --start, re-optimizes every --rebalance days using
only past data, and compares against the Nifty 50 and an equal-weight portfolio.

Run from the project root:
    python scripts/backtest_robo.py
    python scripts/backtest_robo.py --start 2023-01-01 --rebalance 63 --no-risk-model

Writes: reports/robo/backtest_summary.csv
        reports/robo/backtest_summary.json
        reports/robo/backtest_<profile>.png
"""

import argparse
import json
import os
import sys
import warnings

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
warnings.filterwarnings("ignore")

import pandas as pd

from backend.common.data_loader import load_benchmark, load_close_table, load_universe
from backend.robo_advisor.backtest import run_backtest

ap = argparse.ArgumentParser()
ap.add_argument("--start", default="2023-01-01")
ap.add_argument("--end", default=None)
ap.add_argument("--rebalance", type=int, default=63, help="trading days between rebalances (63 = quarterly)")
ap.add_argument("--cost", type=float, default=0.001, help="trading cost per unit turnover")
ap.add_argument("--no-risk-model", action="store_true")
ap.add_argument("--risk-params", default=os.path.join("models", "risk", "gjr_params.json"),
                help="must be trained on data ENDING BEFORE --start (not the live file)")
args = ap.parse_args()

CORE = ["RELIANCE", "TCS", "ITC", "MARUTI", "HINDUNILVR"]
out_dir = os.path.join("reports", "robo")
os.makedirs(out_dir, exist_ok=True)

cap_of = load_universe()
table = load_close_table(list(cap_of))
bench = load_benchmark()

rm = None
if not args.no_risk_model and os.path.exists(args.risk_params):
    from backend.risk_model.service import RiskModel
    rm = RiskModel(args.risk_params)
    trained_to = rm.meta.get("data_to")
    if trained_to and pd.Timestamp(trained_to) >= pd.Timestamp(args.start):
        sys.exit(f"Risk model was trained on data up to {trained_to}, after the backtest start "
                 f"{args.start} - that would use future data. Use the training-split file, "
                 f"a later --start, or --no-risk-model.")
    print(f"Using risk model {args.risk_params} (trained up to {trained_to})")
else:
    print("Running WITHOUT the risk model (historical covariance)")

rows, all_summaries = [], {}
for profile in ("conservative", "balanced", "aggressive"):
    print(f"\nBacktesting {profile}...")
    summary, values = run_backtest(table, bench, cap_of, profile, args.start, args.end,
                                   args.rebalance, cost=args.cost, risk_model=rm,
                                   always_include=CORE)
    all_summaries[profile] = summary
    for name in ("robo_advisor", "equal_weight", "nifty50"):
        rows.append({"profile": profile, "strategy": name, **summary[name]})
        s = summary[name]
        print(f"  {name:<13} CAGR {s['cagr']:6.1%} | vol {s['volatility']:5.1%} | Sharpe {s['sharpe']:5.2f} "
              f"| Sortino {s['sortino']:5.2f} | max DD {s['max_drawdown']:6.1%}")
    print(f"  {summary['rebalances']} rebalances, avg {summary['avg_holdings']} holdings, "
          f"avg turnover {summary['avg_turnover_per_rebalance']:.0%}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 4))
        (values * 100).plot(ax=ax, lw=1.3, color=["#2e6da4", "#c98a00", "#6c757d"])
        ax.set_title(f"Backtest ({profile}): growth of Rs 100, {summary['start']} to {summary['end']}")
        ax.set_ylabel("value (Rs)"); ax.grid(alpha=0.3)
        fig.tight_layout(); fig.savefig(os.path.join(out_dir, f"backtest_{profile}.png"), dpi=130)
        plt.close(fig)
    except Exception as e:
        print(f"(plot skipped: {e})")

pd.DataFrame(rows).to_csv(os.path.join(out_dir, "backtest_summary.csv"), index=False)
with open(os.path.join(out_dir, "backtest_summary.json"), "w") as fh:
    json.dump(all_summaries, fh, indent=2)
print(f"\nSaved results and charts to {out_dir}/")
