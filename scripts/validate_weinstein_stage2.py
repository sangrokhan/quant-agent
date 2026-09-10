import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies"))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)
from loaders import load_equity
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-10_weinstein_stage2_breakout.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

start, end = datetime(2018, 1, 1), datetime(2026, 9, 1)
best_params = dict(sma_window=100, breakout_window=50, sma_slope_lookback=20, max_hold_days=60)

results = {}
for symbol in ["QQQ", "SPY"]:
    price_df = load_equity(symbol, start, end)
    returns = strat.generate_returns(price_df, **best_params)
    signals = strat.generate_signals(price_df, **best_params)
    num_trades = int((signals.diff().fillna(0) == 1).sum())

    sharpe_p, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_p, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    tc_p, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10, num_trades=num_trades, min_net_sharpe=0.5)

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
        r = strat.generate_returns(slice_df, **best_params)
        import vectorbt as vbt
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_p = bool(wf_pass_fraction >= 0.75)
    wf_ev = {
        "metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75,
        "n_splits": n_splits, "per_split_passed": wf_results,
    }

    param_grid_results = {}
    for sw in [100, 150, 200]:
        for bw in [30, 50, 70]:
            p2 = dict(sma_window=sw, breakout_window=bw, sma_slope_lookback=20, max_hold_days=60)
            r2 = strat.generate_returns(price_df, **p2)
            sh_p2, sh_ev2 = check_sharpe_ratio(r2, min_sharpe=1.0)
            param_grid_results[str(p2)] = sh_ev2["value"] if sh_ev2["value"] is not None else 0.0
    ps_p, ps_ev = check_parameter_sensitivity(param_grid_results, max_relative_std=0.5)

    results[symbol] = {
        "num_trades": num_trades,
        "sharpe": {"passed": sharpe_p, **sharpe_ev},
        "max_drawdown": {"passed": mdd_p, **mdd_ev},
        "tc_survival": {"passed": tc_p, **tc_ev},
        "walk_forward": {"passed": wf_p, **wf_ev},
        "param_sensitivity": {"passed": ps_p, **ps_ev},
    }

print(json.dumps(results, indent=2, default=str))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validators_weinstein_stage2.json"), "w") as f:
    json.dump(results, f, indent=2, default=str)
