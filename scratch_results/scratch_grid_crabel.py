import sys, importlib.util, json
sys.path.insert(0, "data")
sys.path.insert(0, "validation")
from datetime import datetime
from loaders import load_equity, load_crypto
from grid_test import run_strategy_grid, GridSpec

spec = importlib.util.spec_from_file_location(
    "crabel_dt", "strategies/2026-09-20_crabel_downthrust_long_bias.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={
        "pivot_left": [4, 10],
        "rsi_exit_level": [55, 65, 75],
        "max_hold_days": [10, 20],
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
print(json.dumps(summary, indent=2, default=str))
with open("grid_result_crabel_downthrust.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
