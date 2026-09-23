import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))

from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies", "2026-09-23_rsi10_sma200_connors_rayner.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

grid_spec = GridSpec(
    param_grid={
        "rsi_entry": [25, 30],
        "rsi_exit": [40, 50],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=grid_spec,
    start=datetime(2018, 1, 1), end=datetime(2026, 9, 1),
)
summary = result.summary()
print(json.dumps(summary, indent=2, default=str))
with open("grid_summary_rsi10_sma200_connors_rayner.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

cells = [{"params": c.params, "asset_class": c.asset_class, "symbol": c.symbol, "vol_regime": c.vol_regime_label, "sharpe": c.sharpe, "mdd": c.mdd, "passed": c.passed} for c in result.cells]
with open("grid_cells_rsi10_sma200_connors_rayner.json", "w") as f:
    json.dump(cells, f, indent=2, default=str)
