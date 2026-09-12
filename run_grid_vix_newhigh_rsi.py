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

strat = load_module(os.path.join(ROOT, "strategies", "2026-09-13_vix_newhigh_rsi_confirm.py"), "vixnh_strat")

from grid_test import run_strategy_grid, GridSpec, GridResult
from loaders import load_equity, load_crypto

start, end = datetime(2018, 1, 1), datetime(2026, 9, 1)

spec = GridSpec(
    param_grid={
        "vix_high_window": [15, 20, 30],
        "vix_rsi_threshold": [60, 65, 70],
    },
    symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
    vol_regime_splits=3,
)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
    spec=spec, start=start, end=end,
)
summary = result.summary()
with open(os.path.join(ROOT, "grid_result_vix_newhigh_rsi.json"), "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str)[:4000])
