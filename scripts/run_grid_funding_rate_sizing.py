import sys, os, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, ".")
from datetime import datetime
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-20_funding_rate_contrarian_sizing.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from grid_test import run_strategy_grid, GridSpec
from loaders import load_crypto

# symbol param must match the traded asset; run separate grids per symbol
# since generate_returns needs symbol= kwarg matching price_df's asset.
import json as _json
from validators import check_sharpe_ratio, check_max_drawdown

START = datetime(2020, 1, 1)
END = datetime(2026, 9, 1)

results = {}
for sym in ["BTC/USDT", "ETH/USDT"]:
    price_df = load_crypto(sym, START, END, interval="1d")
    cells = []
    for sensitivity in [0.4, 0.6, 0.8]:
        for deadband in [0.10, 0.15, 0.20]:
            params = dict(symbol=sym, sensitivity=sensitivity, deadband=deadband)
            returns = strat.generate_returns(price_df, **params)
            sh_pass, sh_ev = check_sharpe_ratio(returns)
            mdd_pass, mdd_ev = check_max_drawdown(returns)
            cells.append({"symbol": sym, "params": params, "sharpe": sh_ev["value"], "sharpe_passed": sh_pass, "mdd": mdd_ev["value"], "mdd_passed": mdd_pass, "passed": sh_pass and mdd_pass})
    results[sym] = cells
    passed = sum(1 for c in cells if c["passed"])
    print(sym, "pass_fraction", passed, "/", len(cells))
    for c in cells:
        print("  ", c["params"]["sensitivity"], c["params"]["deadband"], round(c["sharpe"],3) if c["sharpe"] else None, round(c["mdd"],3), c["passed"])

with open("grid_cells_funding_rate_sizing.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
