import sys
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
from datetime import datetime
import importlib.util
spec_mod = importlib.util.spec_from_file_location("wodtdw", "strategies/2026-09-26_williams_outside_day_tdw_reversal.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={"exclude_weekday": [3, 4, -1], "max_hold_days": [5, 10, 15]},
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
with open("grid_summary_williams_outside_day_tdw.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
