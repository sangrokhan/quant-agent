import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grid_test import run_strategy_grid, GridSpec
from data.loaders import load_equity, load_crypto
import importlib.util

spec = importlib.util.spec_from_file_location("strat_vwbb", "strategies/2026-09-21_vwbb_meanrev_trend_gate.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={
        "window": [15, 20, 30],
        "band_mult": [1.5, 2.0, 2.5],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=gspec,
    start=datetime(2018, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
with open("grid_summary_vwbb_meanrev.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

cells = [{
    "params": c.params, "asset_class": c.asset_class, "symbol": c.symbol,
    "vol_regime": c.vol_regime_label, "sharpe": c.sharpe, "sharpe_passed": c.sharpe_passed,
    "mdd": c.mdd, "mdd_passed": c.mdd_passed, "error": c.error,
} for c in result.cells]
with open("grid_cells_vwbb_meanrev.json", "w") as f:
    json.dump(cells, f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str))
