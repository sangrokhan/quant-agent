import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "validation"))

from loaders import load_equity
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity
import importlib.util

spec_path = os.path.join(os.path.dirname(__file__), "strategies", "2026-09-13_random_forest_direction_classifier.py")
spec = importlib.util.spec_from_file_location("rf_strat", spec_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)
price_df = load_equity("QQQ", start, end)

best_params = {"retrain_period": 126, "max_depth": 3}
returns = strat.generate_returns(price_df, **best_params)
positions = strat.generate_signals(price_df, **best_params)
num_trades = int((positions.diff() == 1).sum())

results = {}
results["sharpe_ratio"] = check_sharpe_ratio(returns, min_sharpe=1.0)
results["max_drawdown"] = check_max_drawdown(returns, max_allowed_mdd=0.25)
results["transaction_cost_survival"] = check_transaction_cost_survival(
    returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5
)

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
wf_e = {
    "metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75,
    "n_splits": n_splits, "per_split_passed": wf_results,
    "note": "manual 4-equal-slice fallback; strategy itself already does rolling walk-forward retraining internally",
}
results["walk_forward"] = (wf_p, wf_e)

# parameter sensitivity: sweep retrain_period/max_depth around chosen values
sens_grid = {}
for rp in [63, 126]:
    for md in [3, 5]:
        r = strat.generate_returns(price_df, retrain_period=rp, max_depth=md)
        try:
            import vectorbt as vbt
            sh = r.vbt.returns(freq="D").sharpe_ratio()
        except Exception:
            sh = None
        sens_grid[str((rp, md))] = float(sh) if sh is not None else 0.0
results["parameter_sensitivity"] = check_parameter_sensitivity(sens_grid, max_relative_std=0.5)

out = {k: {"passed": v[0], "evidence": v[1]} for k, v in results.items()}
out["num_trades"] = num_trades
with open("validators_rf.json", "w") as f:
    json.dump(out, f, indent=2, default=str)
print(json.dumps(out, indent=2, default=str))
