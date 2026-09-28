import sys
sys.path.insert(0, "validation")
sys.path.insert(0, "data")

import importlib.util
from datetime import datetime
import json

spec = importlib.util.spec_from_file_location("bulk2c_strat", "strategies/2026-09-28_bulkowski_2close_bullish_reversal.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity, load_crypto
from grid_test import run_strategy_grid, GridSpec

grid_spec = GridSpec(
    param_grid={
        "target_height_mult": [1.0, 2.0, 3.0],
        "max_hold_days": [15, 25],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=grid_spec,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
print(json.dumps(summary, indent=2, default=str))

with open("grid_summary_bulkowski_2close.json", "w") as f:
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
with open("grid_cells_bulkowski_2close.json", "w") as f:
    json.dump(cells, f, indent=2, default=str)
