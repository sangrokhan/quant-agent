import sys, os, json, importlib.util
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "validation"))
sys.path.insert(0, os.path.join(ROOT, "data"))

def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

strat = load_module(os.path.join(ROOT, "strategies", "2026-09-12_rsmk_relative_strength_crossover.py"), "rsmk_strat")

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)
from loaders import load_equity

best_params = dict(period=60, smooth=3.0, signal_period=10, benchmark_symbol="SPY", max_hold_days=30)
start, end = datetime(2018, 1, 1), datetime(2026, 9, 1)

results = {}
for symbol in ["QQQ", "SPY"]:
    p = dict(best_params)
    if symbol == "SPY":
        # can't benchmark SPY against itself meaningfully -- use QQQ as benchmark instead
        p["benchmark_symbol"] = "QQQ"
    price_df = load_equity(symbol, start, end)
    returns = strat.generate_returns(price_df, **p)
    signals = strat.generate_signals(price_df, **p)
    num_trades = int((signals.diff().fillna(0) == 1).sum())

    sharpe_p, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_p, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
    tc_p, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)

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
        r = strat.generate_returns(slice_df, **p)
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh is not None and sh > 0)
    wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
    wf_p = bool(wf_pass_fraction >= 0.75)
    wf_ev = {
        "metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75,
        "n_splits": n_splits, "per_split_passed": wf_results,
        "note": "manual 4-equal-slice fallback; vbt.utils.splitting.RangeSplitter broken in this install",
    }

    param_grid_results = {}
    for per in [60, 90, 120]:
        for sp in [10, 20, 30]:
            p2 = dict(p); p2["period"] = per; p2["signal_period"] = sp
            r2 = strat.generate_returns(price_df, **p2)
            sh_p2, sh_ev2 = check_sharpe_ratio(r2, min_sharpe=1.0)
            param_grid_results[str((per, sp))] = sh_ev2["value"] if sh_ev2["value"] is not None else 0.0
    ps_p, ps_ev = check_parameter_sensitivity(param_grid_results, max_relative_std=0.5)

    results[symbol] = {
        "benchmark": p["benchmark_symbol"],
        "num_trades": num_trades,
        "sharpe": {"passed": sharpe_p, **sharpe_ev},
        "max_drawdown": {"passed": mdd_p, **mdd_ev},
        "tc_survival": {"passed": tc_p, **tc_ev},
        "walk_forward": {"passed": wf_p, **wf_ev},
        "param_sensitivity": {"passed": ps_p, **ps_ev},
    }

print(json.dumps(results, indent=2, default=str))
with open(os.path.join(ROOT, "validators_rsmk.json"), "w") as f:
    json.dump(results, f, indent=2, default=str)
