import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies"))

from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies", "2026-09-21_xlp_rangeband_ibs_inverse_meanrev.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

grid_spec = GridSpec(
    param_grid={
        "band_window": [10, 25],
        "band_mult": [2.0, 2.5],
        "ibs_threshold": [0.3, 0.4],
    },
    symbols={"equity": ["XLP", "QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
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

with open("grid_result_xlp_rangeband_ibs_inverse.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
