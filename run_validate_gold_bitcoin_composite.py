import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)
from loaders import load_equity
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "gold_btc_composite",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies", "2026-09-23_gold_bitcoin_dual_momentum_composite.py"),
)
strat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(strat)

start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)
price_df = load_equity("GLD", start, end)

primary_params = dict(vol_cap=0.20, lookback_weeks_1=4, lookback_weeks_2=8, lookback_weeks_3=12)
returns = strat.generate_returns(price_df, **primary_params)
signals = strat.generate_signals(price_df, **primary_params)

num_trades = int((signals.diff().abs() > 0).sum())

results = {}
results["sharpe_ratio"] = check_sharpe_ratio(returns, min_sharpe=1.0)
results["max_drawdown"] = check_max_drawdown(returns, max_allowed_mdd=0.25)
results["transaction_cost_survival"] = check_transaction_cost_survival(
    returns, cost_bps_per_trade=10, num_trades=num_trades, min_net_sharpe=0.5
)


def strategy_fn(slice_df):
    return strat.generate_returns(slice_df, **primary_params)


import vectorbt as vbt

n_splits = 4
n = len(price_df)
split_size = n // n_splits
wf_results = []
for i in range(n_splits):
    lo, hi = i * split_size, (i + 1) * split_size if i < n_splits - 1 else n
    slice_df = price_df.iloc[lo:hi]
    if slice_df.empty:
        continue
    r = strategy_fn(slice_df)
    sharpe = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
    wf_results.append(sharpe is not None and sharpe > 0)

wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
results["walk_forward"] = (
    wf_pass_fraction >= 0.75,
    {
        "metric": "walk_forward_pass_fraction",
        "value": wf_pass_fraction,
        "threshold": 0.75,
        "n_splits": n_splits,
        "per_split_passed": wf_results,
        "note": "manual fallback split (vbt.utils.splitting.RangeSplitter unavailable)",
    },
)

# param sensitivity via vol_cap sweep
param_grid_results = {}
for vc in [0.15, 0.20, 0.25]:
    r = strat.generate_returns(price_df, vol_cap=vc, lookback_weeks_1=4, lookback_weeks_2=8, lookback_weeks_3=12)
    import vectorbt as vbt
    sharpe = r.vbt.returns(freq="D").sharpe_ratio()
    param_grid_results[f"vol_cap={vc}"] = float(sharpe) if sharpe is not None else 0.0

results["parameter_sensitivity"] = check_parameter_sensitivity(param_grid_results, max_relative_std=0.5)

out = {k: {"passed": v[0], "evidence": v[1]} for k, v in results.items()}
print(json.dumps(out, indent=2, default=str))
with open("validate_result_gold_bitcoin_composite.json", "w") as f:
    json.dump(out, f, indent=2, default=str)
