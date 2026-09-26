import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "strategies"))

from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
import importlib.util

spec_mod_path = os.path.join(os.path.dirname(__file__), "strategies", "2026-09-26_frontrun_seasonality_percentile.py")
spec = importlib.util.spec_from_file_location("strat", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

grid_spec = GridSpec(
    param_grid={
        "shift_months": [10, 11, 12],
        "percentile_threshold": [0.5, 0.6],
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
with open("grid_result_frontrun_seasonality.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))
