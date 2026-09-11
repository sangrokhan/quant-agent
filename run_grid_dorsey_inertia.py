import sys, os, json, importlib.util
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "validation"))
sys.path.insert(0, os.path.join(ROOT, "data"))

def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

strat = load_module(os.path.join(ROOT, "strategies", "2026-09-12_dorsey_inertia_midline_cross.py"), "inertia_strat")

from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto

spec = GridSpec(
    param_grid={
        "smoothing_period": [10, 20, 30],
        "rvi_period": [7, 10, 14],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)

result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=spec,
    start=datetime(2019, 1, 1),
    end=datetime(2026, 9, 1),
)

summary = result.summary()
with open(os.path.join(ROOT, "grid_result_dorsey_inertia.json"), "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str)[:4000])
