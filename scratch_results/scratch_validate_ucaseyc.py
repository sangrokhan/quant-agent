import sys, importlib.util, json
sys.path.insert(0, "data")
sys.path.insert(0, "validation")
from datetime import datetime
from loaders import load_equity
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)

spec = importlib.util.spec_from_file_location(
    "ultimate_c", "strategies/2026-09-20_ultimate_casey_c_multiscale_meanrev.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

params = dict(lookback=5, entry_level=30, exit_level=65, max_hold_days=7)

price = load_equity("SPY", datetime(2019, 1, 1), datetime(2026, 9, 1))
returns = strat.generate_returns(price, **params)

sharpe_ok, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
mdd_ok, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
sig = strat.generate_signals(price, **params)
num_trades = int((sig.diff() == 1).sum())
tc_ok, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=5.0, num_trades=num_trades)

def strat_fn(price_slice):
    return strat.generate_returns(price_slice, **params)

df_idx = price.set_index("timestamp") if "timestamp" in price.columns else price
n_splits = 4
step = len(df_idx) // n_splits
wf_results = []
for i in range(n_splits):
    s = i * step
    e = len(df_idx) if i == n_splits - 1 else (i + 1) * step
    slice_df = df_idx.iloc[s:e]
    if slice_df.empty:
        continue
    r = strat_fn(slice_df)
    import vectorbt as vbt
    sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
    wf_results.append(sh is not None and sh > 0)
wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
wf_ok = bool(wf_pass_fraction >= 0.75)
wf_ev = {"metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75,
         "n_splits": n_splits, "per_split_passed": wf_results,
         "note": "manual split (vbt.utils.splitting.RangeSplitter unavailable in installed vectorbt version)"}

# param sensitivity from grid json (equity SPY cells around this config)
with open("grid_result_ultimate_casey_c.json") as f:
    gridsum = json.load(f)

param_grid_results = {
    "entry20": None, "entry25": None, "entry30": None,
}
# quick re-derive: rerun a small param sweep for sensitivity purely on SPY low-vol full sample
sens_results = {}
for el in [20, 25, 30]:
    p2 = dict(params); p2["entry_level"] = el
    r2 = strat.generate_returns(price, **p2)
    import vectorbt as vbt
    sh = r2.vbt.returns(freq="D").sharpe_ratio()
    sens_results[f"entry_level_{el}"] = float(sh) if sh is not None else 0.0

sens_ok, sens_ev = check_parameter_sensitivity(sens_results, max_relative_std=0.5)

out = {
    "params": params,
    "sharpe": (sharpe_ok, sharpe_ev),
    "mdd": (mdd_ok, mdd_ev),
    "tc": (tc_ok, tc_ev),
    "walk_forward": (wf_ok, wf_ev),
    "param_sensitivity": (sens_ok, sens_ev),
}
print(json.dumps(out, indent=2, default=str))
with open("validate_result_ultimate_casey_c_spy.json", "w") as f:
    json.dump(out, f, indent=2, default=str)
