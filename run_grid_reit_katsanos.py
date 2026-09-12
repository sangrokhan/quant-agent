import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies"))

from datetime import datetime
from grid_test import run_strategy_grid, GridSpec
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "reit_strat",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies", "2026-09-12_reit_katsanos_rate_gated.py"),
)
strat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(strat)
from loaders import load_equity, load_crypto

spec = GridSpec(
    param_grid={
        "donchian_window": [30, 40, 60],
        "tnx_roc_max": [-0.02, 0.0, 0.05],
    },
    symbols={"equity": ["VNQ", "QQQ"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=spec,
    start=datetime(2015, 1, 1), end=datetime(2026, 9, 1),
)
summary = result.summary()
with open("grid_result_reit_katsanos.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))
