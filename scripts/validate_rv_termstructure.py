import sys, json
from datetime import datetime
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-10_rv_term_structure_regime_gate.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity

results = {}
for sym in ["QQQ", "SPY"]:
    df = load_equity(sym, datetime(2017, 1, 1), datetime(2026, 9, 1))
    params = dict(contango_threshold=0.95, trend_window=50, backwardation_threshold=1.15)
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
    for ct, tw, bt in product([0.85, 0.90, 0.95], [50, 100], [1.05, 1.15]):
        r = strat.generate_returns(df, contango_threshold=ct, trend_window=tw, backwardation_threshold=bt)
        sh = check_sharpe_ratio(r)[1]["value"]
        param_grid_results[f"ct={ct},tw={tw},bt={bt}"] = sh if sh is not None else 0.0
    psens = check_parameter_sensitivity(param_grid_results)

    results[sym] = {"sharpe": sharpe, "mdd": mdd, "tc": tc, "wf": wf, "param_sensitivity": psens, "num_trades": num_trades}

print(json.dumps(results, indent=2, default=str))
with open("validators_rv_termstructure.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
