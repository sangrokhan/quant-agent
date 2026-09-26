import sys
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
from datetime import datetime
import importlib.util
spec_mod = importlib.util.spec_from_file_location("wk", "strategies/2026-09-26_weekly_inside_week_breakout.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={"target_mult": [1.5, 2.0, 3.0], "max_hold_days": [10, 15, 20]},
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=gspec,
    start=datetime(2019, 1, 1), end=datetime(2026, 9, 1),
)
import json
summary = result.summary()
print(json.dumps(summary, indent=2, default=str))
with open("grid_summary_weekly_inside_week_breakout.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
