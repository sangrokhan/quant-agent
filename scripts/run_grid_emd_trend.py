import importlib.util
import sys
from datetime import datetime

sys.path.insert(0, "data")
sys.path.insert(0, "validation")

from loaders import load_equity, load_crypto  # noqa: E402
from grid_test import run_strategy_grid, GridSpec  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-18_ehlers_emd_trend_mode.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

grid_spec = GridSpec(
    param_grid={
        "period": [15, 20, 30],
        "fraction": [3.0, 5.0, 8.0],
        "max_hold_days": [40, 60],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=grid_spec,
    start=datetime(2018, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
import json

print(json.dumps(summary, indent=2, default=str))

with open("grid_cells_emd_trend.json", "w") as f:
    json.dump([c.__dict__ for c in result.cells], f, indent=2, default=str)
