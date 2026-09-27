import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime
from data.loaders import load_equity, load_crypto
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)
import importlib.util

spec = importlib.util.spec_from_file_location("strat_bvlv", "strategies/2026-09-28_better_volume_low_volume_pullback.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

PARAMS = dict(trend_window=50, lookback=30, max_hold_days=30)

all_out = {}
for asset_class, symbol, loader in [
    ("equity", "QQQ", load_equity), ("equity", "SPY", load_equity),
    ("crypto", "BTC/USDT", load_crypto), ("crypto", "ETH/USDT", load_crypto),
]:
    df = loader(symbol, datetime(2019, 1, 1), datetime(2026, 9, 1))
    returns = strat.generate_returns(df, **PARAMS)
    pos = strat.generate_signals(df, **PARAMS)
    num_trades = int((pos.diff().abs() > 0).sum())

    results = {}
    results["sharpe_ratio"] = check_sharpe_ratio(returns)
    results["max_drawdown"] = check_max_drawdown(returns)
    results["transaction_cost_survival"] = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

    df_idx = df.set_index("timestamp") if "timestamp" in df.columns else df
    n_splits = 4
    chunks = np.array_split(df_idx.index, n_splits)
    wf_results = []
    for chunk in chunks:
        if len(chunk) == 0:
            continue
        slice_df = df_idx.loc[chunk]
        r = strat.generate_returns(slice_df.reset_index(), **PARAMS)
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

    param_grid_results = {}
    for lb in [15, 20, 30]:
        p2 = dict(PARAMS); p2["lookback"] = lb
        r = strat.generate_returns(df, **p2)
        import vectorbt as vbt
        sh = r.vbt.returns(freq="D").sharpe_ratio()
        param_grid_results[f"lookback={lb}"] = float(sh) if sh is not None else 0.0
    results["parameter_sensitivity"] = check_parameter_sensitivity(param_grid_results)

    out = {}
    print(f"=== {asset_class}:{symbol} (trades={num_trades}) ===")
    for k, (p, e) in results.items():
        print(" ", k, "PASS" if p else "FAIL", e)
        out[k] = {"passed": p, **e}
    all_out[f"{asset_class}:{symbol}"] = out

json.dump(all_out, open("validators_better_volume_low_volume_pullback.json", "w"), indent=2, default=str)
