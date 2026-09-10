import sys, json
from datetime import datetime
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-10_obv_divergence_swinghigh_confirm.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity

results = {}
for sym in ["QQQ", "SPY"]:
    df = load_equity(sym, datetime(2017, 1, 1), datetime(2026, 9, 1))
    params = dict(lookback=30, trend_window=100, max_hold_days=20)
    returns = strat.generate_returns(df, **params)
    sharpe = check_sharpe_ratio(returns)
    mdd = check_max_drawdown(returns)
    sig = strat.generate_signals(df, **params)
    num_trades = int((sig.diff() == 1).sum())
    tc = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

    n_splits = 4
    idx = df.index
    step = len(idx) // n_splits
    wf_results = []
    for i in range(n_splits):
        s = i * step
        e = len(idx) if i == n_splits - 1 else (i + 1) * step
        slice_df = df.iloc[s:e]
        if slice_df.empty:
            continue
        r = strat.generate_returns(slice_df, **params)
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf = (bool(wf_pass_fraction >= 0.75), {
        "metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75,
        "n_splits": n_splits, "per_split_passed": wf_results,
        "note": "manual split (vbt.utils.splitting.RangeSplitter unavailable in installed vectorbt version)",
    })

    from itertools import product
    param_grid_results = {}
    for lb, tw, mh in product([15, 20, 30], [50, 100], [10, 15, 20]):
        r = strat.generate_returns(df, lookback=lb, trend_window=tw, max_hold_days=mh)
        sh = check_sharpe_ratio(r)[1]["value"]
        param_grid_results[f"lb={lb},tw={tw},mh={mh}"] = sh if sh is not None else 0.0
    psens = check_parameter_sensitivity(param_grid_results)

    results[sym] = {"sharpe": sharpe, "mdd": mdd, "tc": tc, "wf": wf, "param_sensitivity": psens, "num_trades": num_trades}

print(json.dumps(results, indent=2, default=str))
with open("validators_obv_divergence.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
