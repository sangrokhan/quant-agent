import sys, os, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, ".")
from datetime import datetime
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-10_bop_bullish_divergence.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity, load_crypto
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)
import numpy as np
import vectorbt as vbt

start = datetime(2017, 1, 1)
end = datetime(2026, 9, 1)
best_params = dict(swing_window=3, exit_sma_window=10)

results = {}
symbols = [("equity", "QQQ", load_equity), ("equity", "SPY", load_equity),
           ("crypto", "BTC/USDT", load_crypto), ("crypto", "ETH/USDT", load_crypto)]
for asset_class, symbol, loader in symbols:
    df = loader(symbol, start, end)
    returns = strat.generate_returns(df, **best_params)
    sig = strat.generate_signals(df, **best_params)
    num_trades = int((sig.diff().fillna(0) != 0).sum() / 2) + 1

    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns)
    mdd_pass, mdd_ev = check_max_drawdown(returns)
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

    df2 = df.set_index("timestamp") if "timestamp" in df.columns else df
    idx = df2.index
    splits = np.array_split(idx, 4)
    wf_results = []
    for s in splits:
        slice_df = df2.loc[s]
        if slice_df.empty:
            continue
        r = strat.generate_returns(slice_df, **best_params)
        sh = r.vbt.returns(freq="D").sharpe_ratio()
        wf_results.append(bool(sh is not None and sh > 0))
    wf_pass_fraction = sum(wf_results) / len(wf_results) if wf_results else 0.0
    wf_pass = wf_pass_fraction >= 0.75

    param_grid_results = {}
    for sw in [3, 5, 8]:
        for esw in [10, 20]:
            p = dict(swing_window=sw, exit_sma_window=esw)
            r = strat.generate_returns(df, **p)
            sh = r.vbt.returns(freq="D").sharpe_ratio()
            param_grid_results[f"sw{sw}_esw{esw}"] = float(sh) if sh is not None else None
    ps_pass, ps_ev = check_parameter_sensitivity(param_grid_results)

    results[symbol] = {
        "num_trades": num_trades,
        "sharpe": {"passed": sharpe_pass, **sharpe_ev},
        "mdd": {"passed": mdd_pass, **mdd_ev},
        "tc": {"passed": tc_pass, **tc_ev},
        "wf": {"passed": wf_pass, "value": wf_pass_fraction, "threshold": 0.75, "per_split_passed": wf_results,
               "note": "manual 4-split RangeSplitter workaround (vectorbt.utils.splitting unavailable)"},
        "param_sens": {"passed": ps_pass, **ps_ev},
    }

with open("validators_bop_div.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print(json.dumps(results, indent=2, default=str))
