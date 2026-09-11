import sys, os, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, ".")
from datetime import datetime
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-11_turn_of_month_seasonality.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto

grid_spec = GridSpec(
    param_grid={
        "entry_days_before_month_end": [2, 4, 6],
        "exit_days_into_month": [1, 2, 3],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=grid_spec,
    start=datetime(2010, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
with open("grid_result_tom.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str)[:4000])
