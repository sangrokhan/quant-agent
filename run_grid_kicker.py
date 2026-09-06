import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))

from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
import importlib.util
spec_ = importlib.util.spec_from_file_location(
    "kicker_strat",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies", "2026-09-06_bullish_kicker_reversal.py"),
)
strat = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(strat)

spec = GridSpec(
    param_grid={"max_wick_pct": [0.10, 0.15, 0.25], "trend_window": [50, 200]},
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=spec,
    start=datetime(2019, 1, 1), end=datetime(2026, 9, 1),
)
summary = result.summary()
print(json.dumps(summary, indent=2, default=str))
with open("grid_summary_kicker.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
