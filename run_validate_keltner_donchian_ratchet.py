import sys, os, json
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)
from loaders import load_equity, load_crypto
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies", "2026-09-22_keltner_donchian_ratchet_trend.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

start, end = datetime(2018, 1, 1), datetime(2026, 9, 1)

CONFIG = dict(entry_window=15, exit_window=50, keltner_mult=1.5)

results = {}
for symbol in ["QQQ", "SPY"]:
    price_df = load_equity(symbol, start, end)
    returns = strat.generate_returns(price_df, **CONFIG)

    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns)
    mdd_pass, mdd_ev = check_max_drawdown(returns)
    signals = strat.generate_signals(price_df, **CONFIG)
    num_trades = int((signals.diff().fillna(0) != 0).sum())
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

    n_splits = 4
    has_ts = "timestamp" in price_df.columns
    idx = price_df.set_index("timestamp").index if has_ts else price_df.index
    chunks = np.array_split(idx, n_splits)
    wf_results = []
    for chunk in chunks:
        if has_ts:
            slice_df = price_df[price_df["timestamp"].isin(chunk)]
        else:
            slice_df = price_df.loc[price_df.index.isin(chunk)]
        if slice_df.empty:
            continue
        r = strat.generate_returns(slice_df, **CONFIG)
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(bool(sh is not None and sh > 0))
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_pass = bool(wf_pass_fraction >= 0.75)
    wf_ev = {
        "metric": "walk_forward_pass_fraction", "value": wf_pass_fraction,
        "threshold": 0.75, "n_splits": n_splits, "per_split_passed": wf_results,
    }

    grid_results = {}
    for ew in [10, 15, 20]:
        for km in [1.0, 1.5, 2.0]:
            r = strat.generate_returns(price_df, entry_window=ew, exit_window=50, keltner_mult=km)
            sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
            if sh is not None:
                grid_results[f"ew={ew},km={km}"] = sh
    psens_pass, psens_ev = check_parameter_sensitivity(grid_results)

    results[symbol] = {
        "sharpe": (sharpe_pass, sharpe_ev),
        "mdd": (mdd_pass, mdd_ev),
        "tc_survival": (tc_pass, tc_ev),
        "walk_forward": (wf_pass, wf_ev),
        "param_sensitivity": (psens_pass, psens_ev),
    }

print(json.dumps(results, indent=2, default=str))
with open("validate_result_keltner_donchian_ratchet.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
