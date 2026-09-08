import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies"))

import importlib.util
from loaders import load_equity
from validators import (
    check_sharpe_ratio,
    check_max_drawdown,
    check_transaction_cost_survival,
    check_parameter_sensitivity,
)

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-09_rsi_oversold_atr_bracket_exit.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

BEST = {"oversold_thresh": 30, "rr_ratio": 3.0}

results = {}
for sym in ["QQQ", "SPY"]:
    df = load_equity(sym, start=datetime(2019, 1, 1), end=datetime(2026, 9, 1))
    returns = strat.generate_returns(df, **BEST)
    sig = strat.generate_signals(df, **BEST)
    num_trades = int((sig.diff().fillna(0) == 1).sum())

    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_pass, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)

    param_grid_results = {}
    for ot in [25, 30, 35]:
        for rr in [1.5, 2.0, 3.0]:
            r = strat.generate_returns(df, oversold_thresh=ot, rr_ratio=rr)
            try:
                s = check_sharpe_ratio(r)[1]["value"]
            except Exception:
                s = 0.0
            param_grid_results[f"ot{ot}_rr{rr}"] = s if s is not None else 0.0
    ps_pass, ps_ev = check_parameter_sensitivity(param_grid_results)

    results[sym] = {
        "sharpe": {"passed": sharpe_pass, **sharpe_ev},
        "max_drawdown": {"passed": mdd_pass, **mdd_ev},
        "transaction_cost_survival": {"passed": tc_pass, **tc_ev},
        "parameter_sensitivity": {"passed": ps_pass, **ps_ev},
        "num_trades": num_trades,
    }

print(json.dumps(results, indent=2, default=str))
