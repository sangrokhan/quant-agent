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
    "strat",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies",
                 "2026-09-12_kaufman_channel_inside_meanrev.py"),
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

BEST_BY_SYM = {
    "QQQ": {"lrc_window": 20, "zone_factor": 0.35},
    "SPY": {"lrc_window": 40, "zone_factor": 0.1},
}

results = {}
for sym, BEST in BEST_BY_SYM.items():
    df = load_equity(sym, start=datetime(2018, 1, 1), end=datetime(2026, 9, 1))
    returns = strat.generate_returns(df, **BEST)
    sig = strat.generate_signals(df, **BEST)
    num_trades = int((sig.diff().fillna(0) == 1).sum())

    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_pass, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    tc_pass, tc_ev = check_transaction_cost_survival(
        returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5
    )

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
    wf_ev = {
        "metric": "walk_forward_pass_fraction",
        "value": wf_pass_fraction,
        "threshold": 0.75,
        "n_splits": n_splits,
        "per_split_passed": wf_results,
        "note": "manual 4-equal-slice fallback; vbt.utils.splitting.RangeSplitter broken in this install",
    }

    param_grid_results = {}
    for lw in [20, 40, 80]:
        for zf in [0.1, 0.2, 0.35]:
            p = dict(lrc_window=lw, zone_factor=zf)
            r = strat.generate_returns(df, **p)
            import vectorbt as vbt
            try:
                sh = r.vbt.returns(freq="D").sharpe_ratio()
            except Exception:
                sh = None
            param_grid_results[f"lw{lw}_zf{zf}"] = float(sh) if sh == sh and sh is not None else 0.0
    ps_pass, ps_ev = check_parameter_sensitivity(param_grid_results, max_relative_std=0.5)

    results[sym] = {
        "params": BEST,
        "num_trades": num_trades,
        "sharpe": (sharpe_pass, sharpe_ev),
        "mdd": (mdd_pass, mdd_ev),
        "tc": (tc_pass, tc_ev),
        "walk_forward": (wf_pass, wf_ev),
        "param_sensitivity": (ps_pass, ps_ev),
        "all_passed": bool(sharpe_pass and mdd_pass and tc_pass and wf_pass and ps_pass),
    }

print(json.dumps(results, indent=2, default=str))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kaufman_channel_validation.json"), "w") as f:
    json.dump(results, f, indent=2, default=str)
