import sys, os, json
sys.path.insert(0, 'validation')
sys.path.insert(0, 'data')
from datetime import datetime
from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
import importlib.util

spec_path = os.path.join('strategies', '2026-09-12_ou_halflife_zscore_smoothed_fix.py')
spec = importlib.util.spec_from_file_location('strat_mod', spec_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={"entry_z": [1.0, 1.5, 2.0], "smooth_window": [2, 3, 5]},
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=gspec,
    start=datetime(2019, 1, 1), end=datetime(2026, 9, 1),
)
summary = result.summary()
print(json.dumps(summary, indent=2, default=str))
with open('grid_result_ou_halflife_smoothed.json', 'w') as f:
    json.dump(summary, f, default=str)
with open('grid_cells_ou_halflife_smoothed.json', 'w') as f:
    json.dump([c.__dict__ for c in result.cells], f, default=str)
