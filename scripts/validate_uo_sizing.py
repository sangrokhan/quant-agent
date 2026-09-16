import sys, os, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, ".")
from datetime import datetime
import importlib.util

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-17_ultimate_oscillator_sizing_sma_trend.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity, load_crypto
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)

params = dict(sensitivity=0.3, deadband=0.5, leverage_cap=1.0)

results = {}
for label, loader, sym in [("QQQ", load_equity, "QQQ"), ("SPY", load_equity, "SPY"),
                            ("BTC", load_crypto, "BTC/USDT"), ("ETH", load_crypto, "ETH/USDT")]:
    df = loader(sym, datetime(2019,1,1), datetime(2026,9,1))
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

    # parameter sensitivity: sweep sensitivity across {0.3,0.5,0.8}
    psens_grid = {}
    for s_val in [0.3, 0.5, 0.8]:
        p2 = dict(params); p2["sensitivity"] = s_val
        r2 = strat.generate_returns(df, **p2)
        sh2 = r2.vbt.returns(freq="D").sharpe_ratio() if len(r2) else None
        psens_grid[f"sensitivity={s_val}"] = sh2 if sh2 is not None else 0.0
    psens_pass, psens_ev = check_parameter_sensitivity(psens_grid)

    results[label] = {
        "sharpe": {"passed": sharpe_pass, **sharpe_ev},
        "mdd": {"passed": mdd_pass, **mdd_ev},
        "tc": {"passed": tc_pass, **tc_ev, "num_trades": num_trades},
        "wf": {"passed": wf_pass, "value": wf_pass_fraction, "per_split": wf_results, "note": "manual 4-split fallback"},
        "psens": {"passed": psens_pass, **psens_ev},
    }

print(json.dumps(results, indent=2, default=str))
with open("/tmp/uo_sizing_validators.json","w") as f:
    json.dump(results, f, default=str)
