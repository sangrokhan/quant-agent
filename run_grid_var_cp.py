import sys, os, json
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grid_test import run_strategy_grid, GridSpec
from data.loaders import load_equity, load_crypto
import importlib.util

spec_mod = importlib.util.spec_from_file_location("strat_vcp", "strategies/2026-09-22_variance_changepoint_trend_killswitch.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={
        "cp_threshold": [1.5, 2.0, 2.5],
        "cooldown_days": [5, 10, 20],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=gspec,
    start=datetime(2018, 1, 1), end=datetime(2026, 9, 1),
)

summary = result.summary()
print(json.dumps(summary, indent=2, default=str)[:4000])

cells = [c.__dict__ for c in result.cells]
json.dump(cells, open("grid_cells_variance_changepoint_killswitch.json","w"), default=str)
json.dump(summary, open("grid_summary_variance_changepoint_killswitch.json","w"), default=str)
