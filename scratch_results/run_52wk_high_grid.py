import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

from grid_test import run_strategy_grid, GridSpec
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "wk52", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-20_52wk_high_breakout_sma_exit.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

from loaders import load_equity, load_crypto

spec = GridSpec(
    param_grid={
        "lookback_days": [126, 189, 252],
        "exit_sma_window": [100, 150, 200],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=spec,
    start=datetime(2018, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "grid_summary_52wk_high_breakout.json"), "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str))
