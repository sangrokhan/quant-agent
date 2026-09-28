import sys
from datetime import datetime

sys.path.insert(0, "data")
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")

from loaders import load_equity, load_crypto  # noqa: E402
from grid_test import run_strategy_grid, GridSpec  # noqa: E402
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "alma_strat", "strategies/2026-09-28_alma_dual_crossover_trend.py"
)
alma_strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(alma_strat)

spec = GridSpec(
    param_grid={
        "fast_window": [7, 9, 14],
        "slow_window": [21, 34, 50],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=alma_strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=spec,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)

import json
summary = result.summary()
print(json.dumps(summary, indent=2, default=str))

with open("grid_summary_alma_dual_crossover.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

cells = [
    {
        "params": c.params, "asset_class": c.asset_class, "symbol": c.symbol,
        "vol_regime_label": c.vol_regime_label, "sharpe": c.sharpe,
        "sharpe_passed": c.sharpe_passed, "mdd": c.mdd, "mdd_passed": c.mdd_passed,
        "error": c.error,
    }
    for c in result.cells
]
with open("grid_cells_alma_dual_crossover.json", "w") as f:
    json.dump(cells, f, indent=2, default=str)
