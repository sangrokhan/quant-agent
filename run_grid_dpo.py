import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "strategies"))

from loaders import load_equity, load_crypto
from grid_test import run_strategy_grid, GridSpec
import importlib.util

spec_path = os.path.join(os.path.dirname(__file__), "strategies", "2026-09-16_dpo_dist_sizing_sma_trend.py")
spec = importlib.util.spec_from_file_location("dpo_strat", spec_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gs = GridSpec(
    param_grid={
        "dpo_window": [10, 20, 30],
        "sensitivity": [0.4, 0.5, 0.6],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=gs,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
with open("grid_result_dpo.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))
