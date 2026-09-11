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

strat = load_module(os.path.join(ROOT, "strategies", "2026-09-12_rsmk_relative_strength_crossover.py"), "rsmk_strat")

from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto

start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)

def gen_returns_equity(price_df, **params):
    p = dict(params); p.setdefault("benchmark_symbol", "SPY")
    return strat.generate_returns(price_df, **p)

def gen_returns_crypto(price_df, **params):
    p = dict(params); p["benchmark_symbol"] = "BTC/USDT"
    return strat.generate_returns(price_df, **p)

all_cells = []

spec_eq = GridSpec(
    param_grid={"period": [60, 90, 120], "signal_period": [10, 20, 30]},
    symbols={"equity": ["QQQ", "SPY"]},
    vol_regime_splits=3,
)
result_eq = run_strategy_grid(
    generate_returns_fn=gen_returns_equity,
    loader_fn_by_asset_class={"equity": load_equity},
    spec=spec_eq, start=start, end=end,
)
all_cells.extend(result_eq.cells)

spec_cr = GridSpec(
    param_grid={"period": [60, 90, 120], "signal_period": [10, 20, 30]},
    symbols={"crypto": ["ETH/USDT"]},  # ETH vs BTC benchmark (BTC vs itself is degenerate)
    vol_regime_splits=3,
)
result_cr = run_strategy_grid(
    generate_returns_fn=gen_returns_crypto,
    loader_fn_by_asset_class={"crypto": load_crypto},
    spec=spec_cr, start=start, end=end,
)
all_cells.extend(result_cr.cells)

from grid_test import GridResult
merged = GridResult(cells=all_cells)
summary = merged.summary()
with open(os.path.join(ROOT, "grid_result_rsmk.json"), "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str)[:4000])
