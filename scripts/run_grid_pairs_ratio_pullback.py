import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), "validation"))
sys.path.insert(0, os.path.join(os.getcwd(), "data"))
sys.path.insert(0, os.getcwd())
from datetime import datetime
from grid_test import run_strategy_grid, GridSpec
from data.loaders import load_equity, load_crypto
import importlib.util
spec_mod = importlib.util.spec_from_file_location("strat", "strategies/2026-09-17_pairs_ratio_trend_pullback_derrico.py")
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

def gen_returns_equity(price_df, **kwargs):
    kwargs.setdefault("hedge_symbol", "SPY")
    return strat.generate_returns(price_df, **kwargs)

def gen_returns_crypto(price_df, **kwargs):
    kwargs.setdefault("hedge_symbol", "BTC/USDT")
    return strat.generate_returns(price_df, **kwargs)

spec_eq = GridSpec(
    param_grid={
        "fast_length": [8, 12, 20],
        "slow_length": [30, 40],
        "max_hold_days": [15, 25],
    },
    symbols={"equity": ["QQQ"]},
    vol_regime_splits=3,
)
result_eq = run_strategy_grid(
    generate_returns_fn=gen_returns_equity,
    loader_fn_by_asset_class={"equity": load_equity},
    spec=spec_eq,
    start=datetime(2019,1,1), end=datetime(2026,9,1),
)

spec_cr = GridSpec(
    param_grid={
        "fast_length": [8, 12, 20],
        "slow_length": [30, 40],
        "max_hold_days": [15, 25],
    },
    symbols={"crypto": ["ETH/USDT"]},
    vol_regime_splits=3,
)
result_cr = run_strategy_grid(
    generate_returns_fn=gen_returns_crypto,
    loader_fn_by_asset_class={"crypto": load_crypto},
    spec=spec_cr,
    start=datetime(2019,1,1), end=datetime(2026,9,1),
)

all_cells = result_eq.cells + result_cr.cells
total = len(all_cells)
passed = sum(1 for c in all_cells if c.passed)
summary = {
    "metric": "grid_test",
    "total_cells": total,
    "passed_cells": passed,
    "pass_fraction": passed/total if total else 0,
    "equity_summary": result_eq.summary(),
    "crypto_summary": result_cr.summary(),
}
print(json.dumps(summary, indent=2, default=str))
with open("grid_result_pairs_ratio_pullback.json","w") as f:
    json.dump(summary, f, indent=2, default=str)

cells = [dict(params=c.params, asset_class=c.asset_class, symbol=c.symbol, vol_regime=c.vol_regime_label, sharpe=c.sharpe, mdd=c.mdd, passed=c.passed, error=c.error) for c in all_cells]
with open("grid_cells_pairs_ratio_pullback.json","w") as f:
    json.dump(cells, f, indent=2, default=str)
