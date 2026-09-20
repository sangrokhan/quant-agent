import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), "validation"))
sys.path.insert(0, os.path.join(os.getcwd(), "data"))
sys.path.insert(0, os.path.join(os.getcwd(), "strategies"))
from datetime import datetime
from grid_test import run_strategy_grid, GridSpec
from loaders import load_equity, load_crypto
import importlib.util

spec_path = "strategies/2026-09-20_laguerre_rsi_adx_filter.py"
modspec = importlib.util.spec_from_file_location("strat", spec_path)
strat = importlib.util.module_from_spec(modspec)
modspec.loader.exec_module(strat)

gspec = GridSpec(
    param_grid={
        "buy_level": [15.0, 20.0, 25.0],
        "adx_level": [15.0, 20.0, 25.0],
        "alpha": [0.2, 0.3],
    },
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
with open("grid_result_laguerre_rsi_adx.json", "w") as f:
    json.dump(summary, f, default=str)
with open("grid_cells_laguerre_rsi_adx.json", "w") as f:
    json.dump([{
        "params": c.params, "asset_class": c.asset_class, "symbol": c.symbol,
        "vol_regime": c.vol_regime_label, "sharpe": c.sharpe, "mdd": c.mdd,
        "passed": c.passed, "error": c.error,
    } for c in result.cells], f, default=str)
