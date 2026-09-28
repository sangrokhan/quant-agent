import sys
sys.path.insert(0, "validation")
sys.path.insert(0, "data")

import importlib.util
from datetime import datetime
import json

spec = importlib.util.spec_from_file_location("crsi_strat", "strategies/2026-09-28_connorsrsi_oversold_meanrev.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity, load_crypto
from grid_test import run_strategy_grid, GridSpec

# Rescue attempt: tighter oversold_threshold per prior iteration's notes,
# specifically targeting equity (SPY/QQQ) and ETH -- BTC/USDT dropped per
# prior iteration's recommendation not to revisit without a different mechanism.
grid_spec = GridSpec(
    param_grid={
        "oversold_threshold": [3, 5, 8],
        "exit_threshold": [40, 50],
        "max_hold_days": [8, 10],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["ETH/USDT"]},
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

with open("grid_summary_connorsrsi_tight_os.json", "w") as f:
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
with open("grid_cells_connorsrsi_tight_os.json", "w") as f:
    json.dump(cells, f, indent=2, default=str)
