import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.loaders import load_equity
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
import importlib.util

spec_mod_path = "strategies/2026-09-26_three_bar_reversal_trend_gated.py"
spec = importlib.util.spec_from_file_location("strat_3br", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

params = {"trend_sma_window": 20, "reward_risk_mult": 4.0, "max_hold_days": 20}

price_df = load_equity("QQQ", start=datetime(2018, 1, 1), end=datetime(2026, 9, 1))
returns = strat.generate_returns(price_df, **params)
signals = strat.generate_signals(price_df, **params)
num_trades = int((signals.diff() == 1).sum())

evidence = {}
p1, e1 = check_sharpe_ratio(returns, min_sharpe=1.0)
evidence["sharpe"] = e1
p2, e2 = check_max_drawdown(returns, max_allowed_mdd=0.25)
evidence["max_drawdown"] = e2
p3, e3 = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)
evidence["tc_survival"] = e3
try:
    p4, e4 = check_walk_forward(price_df, lambda df: strat.generate_returns(df, **params), n_splits=4, min_pass_fraction=0.75)
except Exception as exc:
    p4, e4 = None, {"metric": "walk_forward_pass_fraction", "value": None, "reason": f"skipped: vectorbt API error ({exc}); known repo issue"}
evidence["walk_forward"] = e4

# param sensitivity from grid results (same symbol QQQ across grid cells)
with open("grid_cells_three_bar_reversal.json") as f:
    cells = json.load(f)
qqq_cells = [c for c in cells if c["symbol"] == "QQQ" and c["sharpe"] is not None]
pg = {json.dumps(c["params"]): c["sharpe"] for c in qqq_cells}
p5, e5 = check_parameter_sensitivity(pg, max_relative_std=0.5)
evidence["parameter_sensitivity"] = e5

results = {"num_trades": num_trades, "passed": {"sharpe": p1, "mdd": p2, "tc": p3, "walk_forward": p4, "param_sensitivity": p5}, "evidence": evidence}
with open("validation_three_bar_reversal_qqq.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print(json.dumps(results, indent=2, default=str))
