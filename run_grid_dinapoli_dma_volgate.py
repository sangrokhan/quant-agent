import sys, os, json
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grid_test import run_strategy_grid, GridSpec
from data.loaders import load_equity, load_crypto
import importlib.util

spec_mod = importlib.util.spec_from_file_location("strat_dinapoli2", "strategies/2026-09-23_dinapoli_triple_dma_trend_alignment.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

def gen_returns_volgated(price_df, **params):
    params = dict(params)
    params["vol_regime_gate"] = True
    return strat.generate_returns(price_df, **params)

gspec = GridSpec(
    param_grid={
        "max_hold_days": [15, 30, 60],
        "long_window": [25, 40],
        "vol_regime_ratio": [0.8, 1.0, 1.2],
    },
    symbols={"equity": ["QQQ", "SPY"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=gen_returns_volgated,
    loader_fn_by_asset_class={"equity": load_equity},
    spec=gspec,
    start=datetime(2018, 1, 1), end=datetime(2026, 9, 1),
)

summary = result.summary()
print(json.dumps(summary, indent=2, default=str)[:4000])

cells = [c.__dict__ for c in result.cells]
json.dump(cells, open("grid_cells_dinapoli_triple_dma_volgate.json","w"), default=str)
json.dump(summary, open("grid_summary_dinapoli_triple_dma_volgate.json","w"), default=str)
