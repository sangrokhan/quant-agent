import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))

from validators import check_sharpe_ratio, check_max_drawdown
from loaders import load_equity
import importlib.util

spec = importlib.util.spec_from_file_location("strat", "strategies/2026-09-23_paa_graduated_crash_protection.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start, end = datetime(2018, 1, 1), datetime(2026, 9, 1)

cells = []
for symbol in ["QQQ", "SPY"]:
    price_df = load_equity(symbol, start, end)
    for mom_months in [10, 13]:
        params = dict(mom_months=mom_months, n_select=6, cp_denominator=6, primary_symbol=symbol)
        try:
            returns = strat.generate_returns(price_df, **params)
            sharpe_passed, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
            mdd_passed, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
            cells.append({
                "symbol": symbol, "params": params,
                "sharpe": sharpe_ev["value"], "mdd": mdd_ev["value"],
                "passed": sharpe_passed and mdd_passed,
            })
            print(symbol, mom_months, "sharpe=", sharpe_ev["value"], "mdd=", mdd_ev["value"])
        except Exception as exc:
            print(symbol, mom_months, "ERROR", exc)
            cells.append({"symbol": symbol, "params": params, "error": str(exc)})

with open("grid_cells_paa_graduated_crash_protection.json", "w") as f:
    json.dump(cells, f, indent=2, default=str)
