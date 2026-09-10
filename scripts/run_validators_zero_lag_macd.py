import sys, os, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, ".")
from datetime import datetime
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-10_zero_lag_macd_crossover.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity, load_crypto
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)

start = datetime(2017, 1, 1)
end = datetime(2026, 9, 1)

best_params = dict(trend_window=100, signal_period=14)

results = {}
for symbol in ["SPY", "QQQ"]:
    df = load_equity(symbol, start, end)
    returns = strat.generate_returns(df, **best_params)
    sig = strat.generate_signals(df, **best_params)
    num_trades = int((sig.diff().fillna(0) != 0).sum() / 2) + 1

    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns)
    mdd_pass, mdd_ev = check_max_drawdown(returns)
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)
    try:
        strat_fn = lambda price_slice: strat.generate_returns(price_slice, **best_params)
        wf_pass, wf_ev = check_walk_forward(df, strat_fn)
    except Exception as e:
        wf_pass, wf_ev = False, {"error": str(e)}

    param_grid_results = {}
    for tw in [50, 100, 150]:
        for sp in [9, 14]:
            p = dict(trend_window=tw, signal_period=sp)
            r = strat.generate_returns(df, **p)
            import vectorbt as vbt
            sh = r.vbt.returns(freq="D").sharpe_ratio()
            param_grid_results[f"tw{tw}_sp{sp}"] = float(sh) if sh is not None else None
    try:
        ps_pass, ps_ev = check_parameter_sensitivity(param_grid_results)
    except Exception as e:
        ps_pass, ps_ev = False, {"error": str(e)}

    results[symbol] = {
        "num_trades": num_trades,
        "sharpe": {"passed": sharpe_pass, **sharpe_ev},
        "mdd": {"passed": mdd_pass, **mdd_ev},
        "tc": {"passed": tc_pass, **tc_ev},
        "wf": {"passed": wf_pass, **wf_ev},
        "param_sens": {"passed": ps_pass, **ps_ev},
    }

with open("validators_zero_lag_macd.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print(json.dumps(results, indent=2, default=str))
