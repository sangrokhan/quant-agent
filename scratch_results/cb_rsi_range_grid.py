import importlib.util
import sys
import json
from datetime import datetime

sys.path.insert(0, "data")
sys.path.insert(0, "validation")

spec = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-18_constance_brown_rsi_range_shift.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity, load_crypto  # noqa: E402
from grid_test import run_strategy_grid, GridSpec  # noqa: E402

spec_grid = GridSpec(
    param_grid={"bull_support_level": [35, 40, 45], "trend_window": [150, 200]},
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=spec_grid,
    start=datetime(2016, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
print(json.dumps(summary, indent=2, default=str))

with open("grid_cells_constance_brown_rsi_range_shift.json", "w") as f:
    json.dump([c.__dict__ for c in result.cells], f, indent=2, default=str)
with open("grid_summary_constance_brown_rsi_range_shift.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
