import sys, os, json
from datetime import datetime
import itertools

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies"))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)
from loaders import load_equity
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-06_double_bottom_breakout.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

start, end = datetime(2015, 1, 1), datetime(2026, 9, 1)
param_combos = list(itertools.product([3,5], [0.02,0.03,0.05], [20]))

for symbol in ["QQQ", "SPY"]:
    price_df = load_equity(symbol, start, end)
    best_sharpe = -999
    best_params = None
    for sw, lsp, mh in param_combos:
        p = {"swing_window": sw, "low_similarity_pct": lsp, "max_hold_days": mh}
        r = strat.generate_returns(price_df, **p)
        s_passed, s_ev = check_sharpe_ratio(r, min_sharpe=1.0)
        val = s_ev["value"] if s_ev["value"] is not None else -999
        if val > best_sharpe:
            best_sharpe = val
            best_params = p
    print(f"{symbol} best full-sample config: {best_params} sharpe={best_sharpe}")

    returns = strat.generate_returns(price_df, **best_params)
    sharpe_passed, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_passed, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    positions = strat.generate_signals(price_df, **best_params)
    num_trades = int(((positions.shift(1).fillna(0) == 0) & (positions == 1)).sum())
    tc_passed, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10, num_trades=num_trades, min_net_sharpe=0.5)

    param_grid_results = {}
    for sw, lsp, mh in param_combos:
        p2 = {"swing_window": sw, "low_similarity_pct": lsp, "max_hold_days": mh}
        r2 = strat.generate_returns(price_df, **p2)
        s2_passed, s2_ev = check_sharpe_ratio(r2, min_sharpe=1.0)
        param_grid_results[str(p2)] = s2_ev["value"] if s2_ev["value"] is not None else 0.0
    ps_passed, ps_ev = check_parameter_sensitivity(param_grid_results, max_relative_std=0.5)

    print("sharpe:", sharpe_passed, sharpe_ev)
    print("mdd:", mdd_passed, mdd_ev)
    print("tc:", tc_passed, tc_ev)
    print("param_sens:", ps_passed, ps_ev)
    print()
