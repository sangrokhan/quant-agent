import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies"))

from datetime import datetime
from grid_test import run_strategy_grid, GridSpec
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "bufi_strat",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies", "2026-09-12_bufi_adaptive_rsi_threshold.py"),
)
strat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(strat)
from loaders import load_equity, load_crypto

spec = GridSpec(
    param_grid={
        "rsi_len": [2, 4],
        "buy_level": [10, 14, 20],
        "adap_k": [3.0, 6.0],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=spec,
    start=datetime(2018, 1, 1), end=datetime(2026, 9, 1),
)
summary = result.summary()
with open("grid_result_bufi_adaptive_rsi.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str)[:4000])
