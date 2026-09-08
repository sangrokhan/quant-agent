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
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-09_hma_crossover_spy_refined.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

BEST = {"hma_window": 100}

results = {}
for sym in ["QQQ", "SPY"]:
    df = load_equity(sym, start=datetime(2019, 1, 1), end=datetime(2026, 9, 1))
    returns = strat.generate_returns(df, **BEST)
    sig = strat.generate_signals(df, **BEST)
    num_trades = int((sig.diff().fillna(0) == 1).sum())

    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_pass, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)

    n_splits = 4
    idx = df.index
    slice_len = len(idx) // n_splits
    wf_results = []
    for i in range(n_splits):
        s = i * slice_len
        e = (i + 1) * slice_len if i < n_splits - 1 else len(idx)
        slice_df = df.iloc[s:e]
        if slice_df.empty:
            continue
        r = strat.generate_returns(slice_df, **BEST)
        import vectorbt as vbt
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_pass = bool(wf_pass_fraction >= 0.75)

    param_grid_results = {}
    for hw in [80, 100, 120]:
        r = strat.generate_returns(df, hma_window=hw)
        try:
            s = check_sharpe_ratio(r)[1]["value"]
        except Exception:
            s = 0.0
        param_grid_results[f"hw{hw}"] = s if s is not None else 0.0
    ps_pass, ps_ev = check_parameter_sensitivity(param_grid_results)

    results[sym] = {
        "sharpe": {"passed": sharpe_pass, **sharpe_ev},
        "max_drawdown": {"passed": mdd_pass, **mdd_ev},
        "transaction_cost_survival": {"passed": tc_pass, **tc_ev},
        "walk_forward": {"passed": wf_pass, "value": wf_pass_fraction, "threshold": 0.75, "per_split_passed": wf_results},
        "parameter_sensitivity": {"passed": ps_pass, **ps_ev},
        "num_trades": num_trades,
    }

print(json.dumps(results, indent=2, default=str))
