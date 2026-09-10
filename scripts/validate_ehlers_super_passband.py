import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies"))

from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity
from loaders import load_equity
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-11_ehlers_super_passband.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

start = datetime(2018, 1, 1)
end = datetime(2026, 9, 1)

per_symbol_params = {
    "QQQ": {"period1": 30, "period2": 60, "trend_window": 100, "max_hold_days": 25},
    "SPY": {"period1": 50, "period2": 60, "trend_window": 100, "max_hold_days": 25},
}

results = {}
for symbol, best_params in per_symbol_params.items():
    price_df = load_equity(symbol, start=start, end=end)
    returns = strat.generate_returns(price_df, **best_params)
    position = strat.generate_signals(price_df, **best_params)
    n_trades = int((position.diff().fillna(0) == 1).sum())

    sharpe_pass, sharpe_ev = check_sharpe_ratio(returns)
    mdd_pass, mdd_ev = check_max_drawdown(returns)
    tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10, num_trades=n_trades)

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
    wf_pass = bool(wf_pass_fraction >= 0.75)
    wf_ev = {
        "metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75,
        "n_splits": n_splits, "per_split_passed": wf_results,
    }

    base_p1 = best_params["period1"]
    base_mhd = best_params["max_hold_days"]
    grid_results = {}
    for p1 in sorted(set([max(10, base_p1 - 10), base_p1, base_p1 + 10])):
        for mhd in [max(5, base_mhd - 5), base_mhd, base_mhd + 5]:
            p = dict(best_params)
            p["period1"] = p1
            p["max_hold_days"] = mhd
            r = strat.generate_returns(price_df, **p)
            try:
                import vectorbt as vbt
                sh = r.vbt.returns(freq="D").sharpe_ratio()
            except Exception:
                sh = None
            grid_results[str(p)] = float(sh) if sh is not None else 0.0
    ps_pass, ps_ev = check_parameter_sensitivity(grid_results)

    results[symbol] = {
        "params": best_params,
        "n_trades": n_trades,
        "sharpe": {"passed": sharpe_pass, **sharpe_ev},
        "max_drawdown": {"passed": mdd_pass, **mdd_ev},
        "tc_survival": {"passed": tc_pass, **tc_ev},
        "walk_forward": {"passed": wf_pass, **wf_ev},
        "param_sensitivity": {"passed": ps_pass, **ps_ev},
    }

print(json.dumps(results, indent=2, default=str))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validators_ehlers_super_passband.json"), "w") as f:
    json.dump(results, f, indent=2, default=str)
