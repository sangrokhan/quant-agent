import sys, os, json
from datetime import datetime
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)
from data.loaders import load_equity
import importlib.util

spec = importlib.util.spec_from_file_location(
    "strat_vixskew", "strategies/2026-09-23_vix_skew_divergence_riskoff.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

params = dict(skew_threshold=135, vix_threshold=15, trend_window=40)

all_results = {}
for asset_class, symbol, loader in [
    ("equity", "SPY", load_equity),
    ("equity", "QQQ", load_equity),
]:
    df = loader(symbol, datetime(2018, 1, 1), datetime(2026, 9, 1))
    returns = strat.generate_returns(df, **params)
    n_trades = int((strat.generate_signals(df, **params).diff().abs() > 0).sum())

    results = {}
    results["sharpe_ratio"] = check_sharpe_ratio(returns)
    results["max_drawdown"] = check_max_drawdown(returns)
    results["transaction_cost_survival"] = check_transaction_cost_survival(
        returns, cost_bps_per_trade=10.0, num_trades=n_trades
    )

    def _strat_fn(price_slice):
        return strat.generate_returns(price_slice, **params)

    df_idx = df.set_index("timestamp") if "timestamp" in df.columns else df
    n_splits = 4
    chunks = np.array_split(df_idx.index, n_splits)
    wf_results = []
    for chunk in chunks:
        if len(chunk) == 0:
            continue
        slice_df = df_idx.loc[chunk]
        r = _strat_fn(slice_df.reset_index())
        sharpe = None
        if len(r):
            import vectorbt as vbt
            sharpe = r.vbt.returns(freq="D").sharpe_ratio()
        wf_results.append(bool(sharpe is not None and sharpe > 0))
    wf_pass_fraction = sum(wf_results) / len(wf_results) if wf_results else 0.0
    results["walk_forward"] = (wf_pass_fraction >= 0.75, {
        "metric": "walk_forward_pass_fraction", "value": wf_pass_fraction,
        "threshold": 0.75, "n_splits": n_splits, "per_split_passed": wf_results,
    })

    # param sensitivity: sweep trend_window/skew/vix locally around new best
    import itertools
    param_grid_results = {}
    for st, vt, tw in itertools.product([130, 135, 140], [15, 18], [35, 40, 45]):
        p = {"skew_threshold": st, "vix_threshold": vt, "trend_window": tw}
        r = strat.generate_returns(df, **p)
        sh_val = check_sharpe_ratio(r)[1].get("value", 0.0)
        param_grid_results[str(p)] = sh_val
    results["parameter_sensitivity"] = check_parameter_sensitivity(param_grid_results)

    all_results[f"{asset_class}_{symbol}"] = {
        k: {"passed": p, "evidence": e} for k, (p, e) in results.items()
    }
    print(f"=== {asset_class}_{symbol} ===")
    for k, (p, e) in results.items():
        print(k, p, e)

with open("validators_vix_skew_divergence_spy_finetune.json", "w") as f:
    json.dump(all_results, f, indent=2, default=str)
