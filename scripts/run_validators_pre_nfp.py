import sys, json
from datetime import datetime
sys.path.insert(0, "data")
sys.path.insert(0, "validation")
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-12_pre_nfp_close_to_close_drift.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity

params = dict(hold_days_before=1, hold_days_after=0)  # best grid cell config

out = {}
for symbol in ["QQQ", "SPY"]:
    df = load_equity(symbol, datetime(2016, 1, 1), datetime(2026, 9, 1))
    if "timestamp" in df.columns:
        df2 = df.set_index("timestamp").sort_index()
    else:
        df2 = df.sort_index()

    returns = strat.generate_returns(df, **params)
    sig = strat.generate_signals(df, **params)
    num_trades = int((sig.diff().fillna(0) == 1).sum())

    sharpe = check_sharpe_ratio(returns)
    mdd = check_max_drawdown(returns)
    tc = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

    n_splits = 4
    idx = df2.index
    step = len(idx) // n_splits
    wf_results = []
    for i in range(n_splits):
        s = i * step
        e = len(idx) if i == n_splits - 1 else (i + 1) * step
        slice_df = df2.iloc[s:e]
        if slice_df.empty:
            continue
        r = strat.generate_returns(slice_df, **params)
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf = (bool(wf_pass_fraction >= 0.75), {
        "metric": "walk_forward_pass_fraction",
        "value": wf_pass_fraction,
        "threshold": 0.75,
        "n_splits": n_splits,
        "per_split_passed": wf_results,
        "note": "manual split (vbt.utils.splitting.RangeSplitter unavailable in installed vectorbt version)",
    })

    from itertools import product
    param_grid_results = {}
    for hb, ha in product([1, 2], [0, 1]):
        rr = strat.generate_returns(df, hold_days_before=hb, hold_days_after=ha)
        sh = check_sharpe_ratio(rr)[1]["value"]
        param_grid_results[f"hb={hb},ha={ha}"] = sh if sh is not None else 0.0
    psens = check_parameter_sensitivity(param_grid_results)

    out[symbol] = {
        "num_trades": num_trades,
        "sharpe": sharpe[1], "sharpe_passed": sharpe[0],
        "mdd": mdd[1], "mdd_passed": mdd[0],
        "tc": tc[1], "tc_passed": tc[0],
        "wf": wf[1], "wf_passed": wf[0],
        "param_sensitivity": psens[1], "param_sensitivity_passed": psens[0],
    }

print(json.dumps(out, indent=2, default=str))
