import sys, os, json
from datetime import datetime

sys.path.insert(0, "data")
sys.path.insert(0, "validation")
sys.path.insert(0, "strategies")

from loaders import load_equity, load_crypto
from grid_test import run_strategy_grid, GridSpec
import importlib.util

spec_path = "strategies/2026-09-23_rsi2_volzscore_atrpct_stacked_gate.py"
spec = importlib.util.spec_from_file_location("strat", spec_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={
        "entry_threshold": [5, 10],
        "exit_threshold": [60, 70],
        "vol_z_threshold": [0.5, 1.0],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=gspec,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
with open("grid_summary_rsi2_volzscore_atrpct_stacked.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))
