import sys, json
from datetime import datetime
sys.path.insert(0, "data")
sys.path.insert(0, "validation")
sys.path.insert(0, "strategies")
from loaders import load_equity  # noqa: E402
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
import importlib.util
spec = importlib.util.spec_from_file_location("strat", "strategies/2026-09-27_broadening_top_bottom_reversal.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start, end = datetime(2018, 1, 1), datetime(2026, 9, 1)
params = dict(touch_tolerance=0.02, min_touches=3, max_hold_days=15)

results = {}
for symbol in ["QQQ", "SPY"]:
    df = load_equity(symbol, start, end)
    returns = strat.generate_returns(df, **params)
    pos = strat.generate_signals(df, **params)
    num_trades = int((pos.diff().abs() > 0).sum())

    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns)
    mdd_pass, mdd_ev = check_max_drawdown(returns)
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

    def strat_fn(slice_df):
        return strat.generate_returns(slice_df, **params)
    try:
        wf_pass, wf_ev = check_walk_forward(df, strat_fn, n_splits=4)
    except Exception as e:
        wf_pass, wf_ev = False, {"error": str(e)}

    # param sensitivity from grid summary values for this symbol not directly available here;
    # do a small local sweep
    grid_results = {}
    for tt in [0.01, 0.015, 0.02]:
        for mt in [3, 4]:
            p = dict(touch_tolerance=tt, min_touches=mt, max_hold_days=15)
            r = strat.generate_returns(df, **p)
            try:
                s = r.vbt.returns(freq="D").sharpe_ratio()
            except Exception:
                s = None
            if s is not None:
                grid_results[str(p)] = float(s)
    ps_pass, ps_ev = check_parameter_sensitivity(grid_results)

    results[symbol] = {
        "num_trades": num_trades,
        "sharpe": (sharpe_pass, sharpe_ev),
        "mdd": (mdd_pass, mdd_ev),
        "tc": (tc_pass, tc_ev),
        "wf": (wf_pass, wf_ev),
        "param_sensitivity": (ps_pass, ps_ev),
    }

print(json.dumps(results, indent=2, default=str))
with open("validate_result_broadening_top_bottom.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
