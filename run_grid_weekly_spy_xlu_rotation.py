import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grid_test import run_strategy_grid, GridSpec
from data.loaders import load_equity
import importlib.util

spec_mod_path = "strategies/2026-09-23_weekly_spy_xlu_relative_performance_rotation.py"
spec = importlib.util.spec_from_file_location("strat_spyxlu", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={
        "lookback_days": [10, 20, 40],
        "rebalance_days": [5, 10],
    },
    symbols={"equity": ["QQQ", "SPY"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity},
    spec=gspec,
    start=datetime(2018, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
with open("grid_summary_weekly_spy_xlu_rotation.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

cells = [{
    "params": c.params, "asset_class": c.asset_class, "symbol": c.symbol,
    "vol_regime": c.vol_regime_label, "sharpe": c.sharpe, "sharpe_passed": c.sharpe_passed,
    "max_drawdown": getattr(c, "max_drawdown", None),
    "mdd_passed": getattr(c, "mdd_passed", None),
} for c in result.cells]
with open("grid_cells_weekly_spy_xlu_rotation.json", "w") as f:
    json.dump(cells, f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str))
