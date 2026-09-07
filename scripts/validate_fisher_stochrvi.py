import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies"))

from loaders import load_equity
from validators import (
    check_sharpe_ratio,
    check_max_drawdown,
    check_transaction_cost_survival,
    check_parameter_sensitivity,
)
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-08_fisher_stochastic_rvi_crossover.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

best_params = dict(rvi_length=14, stoch_length=14, fisher_smooth=5, max_hold_days=15)

start, end = datetime(2015, 1, 1), datetime(2026, 9, 1)
price_qqq = load_equity("QQQ", start, end)

returns = strat.generate_returns(price_qqq, **best_params)
positions = strat.generate_signals(price_qqq, **best_params)
num_trades = int((positions.diff() == 1).sum())

sharpe_pass, sharpe_ev = check_sharpe_ratio(returns, min_sharpe=1.0)
mdd_pass, mdd_ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)
# Manual 4-equal-slice walk-forward fallback (vbt.utils.splitting.RangeSplitter
# is broken in this install, documented since 2026-09-03-002).
n_splits = 4
idx = price_qqq.index
slice_len = len(idx) // n_splits
wf_results = []
for i in range(n_splits):
    s = i * slice_len
    e = (i + 1) * slice_len if i < n_splits - 1 else len(idx)
    slice_df = price_qqq.iloc[s:e]
    if slice_df.empty:
        continue
    r = strat.generate_returns(slice_df, **best_params)
    import vectorbt as vbt
    sharpe = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
    wf_results.append(sharpe is not None and sharpe > 0)
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

# param sensitivity from grid results file (produced by run_iter_fisher_stochrvi.py)
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "grid_result_fisher_stochrvi.json")) as f:
    grid_summary = json.load(f)

# Build param_grid_results from raw cell sharpes on QQQ equity only for sensitivity check
import importlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
from grid_test import run_strategy_grid, GridSpec
from loaders import load_crypto

gspec = GridSpec(
    param_grid={"rvi_length": [10, 14], "stoch_length": [14, 20], "fisher_smooth": [3, 5], "max_hold_days": [15]},
    symbols={"equity": ["QQQ"]},
    vol_regime_splits=1,
)
result = run_strategy_grid(
    generate_returns_fn=strat.generate_returns,
    loader_fn_by_asset_class={"equity": load_equity},
    spec=gspec, start=start, end=end,
)
param_grid_results = {}
for c in result.cells:
    key = json.dumps(c.params, sort_keys=True)
    if c.sharpe is not None:
        param_grid_results[key] = c.sharpe

ps_pass, ps_ev = check_parameter_sensitivity(param_grid_results, max_relative_std=0.5)

out = {
    "best_params": best_params,
    "num_trades": num_trades,
    "sharpe": {"passed": sharpe_pass, **sharpe_ev},
    "max_drawdown": {"passed": mdd_pass, **mdd_ev},
    "tc_survival": {"passed": tc_pass, **tc_ev},
    "walk_forward": {"passed": wf_pass, **wf_ev},
    "param_sensitivity": {"passed": ps_pass, **ps_ev},
}
print(json.dumps(out, indent=2, default=str))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validators_result_fisher_stochrvi.json"), "w") as f:
    json.dump(out, f, indent=2, default=str)
