import sys, json
from datetime import datetime
sys.path.insert(0, "data")
sys.path.insert(0, "validation")
from loaders import load_equity, load_crypto
from grid_test import run_strategy_grid, GridSpec
import importlib.util

spec_path = "strategies/2026-09-23_atr_liquidity_sweep_lowvol_gate_rescue.py"
mspec = importlib.util.spec_from_file_location("strat", spec_path)
strat = importlib.util.module_from_spec(mspec)
mspec.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={
        "swing_window": [10, 20],
        "poke_atr_mult": [0.3, 0.5],
        "confirm_bars": [3, 5],
        "vol_regime_ratio": [0.9, 1.0],
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
with open("grid_summary_atr_liquidity_sweep_lowvol_gate_rescue.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))
