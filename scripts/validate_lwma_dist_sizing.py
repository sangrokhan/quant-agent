import sys, os, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, ".")
from datetime import datetime
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-17_lwma_dist_sizing_dual_window.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity, load_crypto
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)

configs = {
    "QQQ": dict(loader=load_equity, sym="QQQ", params=dict(short_lwma_window=10, long_lwma_window=80, sensitivity=0.5, deadband=0.20)),
    "SPY": dict(loader=load_equity, sym="SPY", params=dict(short_lwma_window=5, long_lwma_window=80, sensitivity=0.5, deadband=0.20)),
    "BTC": dict(loader=load_crypto, sym="BTC/USDT", params=dict(short_lwma_window=5, long_lwma_window=80, sensitivity=0.5, deadband=0.15, leverage_cap=0.3, base_exposure=0.15)),
    "ETH": dict(loader=load_crypto, sym="ETH/USDT", params=dict(short_lwma_window=5, long_lwma_window=80, sensitivity=0.5, deadband=0.20, leverage_cap=0.3, base_exposure=0.15)),
}

results = {}
for label, cfg in configs.items():
    loader = cfg["loader"]; sym = cfg["sym"]; params = cfg["params"]
    df = loader(sym, datetime(2019, 1, 1), datetime(2026, 9, 1))
    returns = strat.generate_returns(df, **params)
    pos = strat.generate_signals(df, **params)
    num_trades = int((pos.diff().abs() > 1e-9).sum())
    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns)
    mdd_pass, mdd_ev = check_max_drawdown(returns)
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

    n_splits = 4
    split_size = len(df) // n_splits
    wf_results = []
    for s in range(n_splits):
        lo = s * split_size
        hi = len(df) if s == n_splits - 1 else (s + 1) * split_size
        slice_df = df.iloc[lo:hi]
        if len(slice_df) < 60:
            continue
        r = strat.generate_returns(slice_df, **params)
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_pass = wf_pass_fraction >= 0.75

    psens_grid = {}
    for s_val in [0.3, 0.5, 0.7]:
        p2 = dict(params); p2["sensitivity"] = s_val
        r2 = strat.generate_returns(df, **p2)
        sh2 = r2.vbt.returns(freq="D").sharpe_ratio() if len(r2) else None
        psens_grid[f"sensitivity={s_val}"] = sh2 if sh2 is not None else 0.0
    psens_pass, psens_ev = check_parameter_sensitivity(psens_grid)

    results[label] = {
        "params": params,
        "sharpe": {"passed": sharpe_pass, **sharpe_ev},
        "mdd": {"passed": mdd_pass, **mdd_ev},
        "tc": {"passed": tc_pass, **tc_ev, "num_trades": num_trades},
        "wf": {"passed": wf_pass, "value": wf_pass_fraction, "per_split": wf_results, "note": "manual 4-split fallback"},
        "psens": {"passed": psens_pass, **psens_ev},
    }

print(json.dumps(results, indent=2, default=str))
with open("/tmp/lwma_validators.json", "w") as f:
    json.dump(results, f, default=str)
