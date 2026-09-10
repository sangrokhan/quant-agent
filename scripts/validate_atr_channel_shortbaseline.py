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
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-10_atr_channel_breakout_shortbaseline.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

start = datetime(2018, 1, 1)
end = datetime(2026, 9, 1)

BEST = dict(baseline_window=100, atr_mult=4.0, max_hold_days=40)

results = {}
for sym in ["QQQ", "SPY"]:
    price_df = load_equity(sym, start, end)
    returns = strat.generate_returns(price_df, **BEST)
    pos = strat.generate_signals(price_df, **BEST)
    num_trades = int((pos.diff() == 1).sum())

    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_pass, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)

    idx_df = price_df.set_index("timestamp") if "timestamp" in price_df.columns else price_df
    n_splits = 4
    slice_len = len(idx_df) // n_splits
    wf_results = []
    for i in range(n_splits):
        s = i * slice_len
        e = (i + 1) * slice_len if i < n_splits - 1 else len(idx_df)
        slice_df = idx_df.iloc[s:e]
        if slice_df.empty:
            continue
        r = strat.generate_returns(slice_df, **BEST)
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_pass = bool(wf_pass_fraction >= 0.75)
    wf_ev = {
        "metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75,
        "n_splits": n_splits, "per_split_passed": wf_results,
        "note": "manual 4-equal-slice fallback; vbt.utils.splitting.RangeSplitter broken in this install",
    }

    # param sensitivity from grid result file (already computed atr_mult sweep at this baseline_window)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "grid_result_atr_channel_shortbaseline.json")) as f:
        grid_summary = json.load(f)

    param_grid_results = {}
    for atr_mult in [3.0, 4.0, 5.0]:
        params = dict(BEST)
        params["atr_mult"] = atr_mult
        r = strat.generate_returns(price_df, **params)
        try:
            sh = r.vbt.returns(freq="D").sharpe_ratio()
        except Exception:
            sh = None
        if sh is not None:
            param_grid_results[str(atr_mult)] = float(sh)

    ps_pass, ps_ev = check_parameter_sensitivity(param_grid_results, max_relative_std=0.5)

    results[sym] = {
        "num_trades": num_trades,
        "sharpe": {"passed": sharpe_pass, **sharpe_ev},
        "max_drawdown": {"passed": mdd_pass, **mdd_ev},
        "tc_survival": {"passed": tc_pass, **tc_ev},
        "walk_forward": {"passed": wf_pass, **wf_ev},
        "param_sensitivity": {"passed": ps_pass, **ps_ev},
    }

print(json.dumps(results, indent=2, default=str))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validate_result_atr_channel_shortbaseline.json"), "w") as f:
    json.dump(results, f, indent=2, default=str)
