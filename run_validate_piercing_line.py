import sys, os, json
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity
from data.loaders import load_equity
import importlib.util
import vectorbt as vbt

spec = importlib.util.spec_from_file_location("strat_pl", "strategies/2026-09-27_piercing_line_reversal.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

params = dict(body_mult=0.75, reclaim_frac_min=0.4, reward_r_multiple=2.0, max_hold_days=12)
price = load_equity("SPY", start=datetime(2019,1,1), end=datetime(2026,9,1))
returns = strat.generate_returns(price, **params)
signals = strat.generate_signals(price, **params)
num_trades = int((signals.diff() == 1).sum())

sharpe_pass, sharpe_ev = check_sharpe_ratio(returns)
mdd_pass, mdd_ev = check_max_drawdown(returns)
tc_pass, tc_ev = check_transaction_cost_survival(returns, cost_bps_per_trade=10, num_trades=num_trades)

n_splits = 4
idx = price.index
split_size = len(idx) // n_splits
wf_results = []
for i in range(n_splits):
    s, e = i * split_size, (i + 1) * split_size if i < n_splits - 1 else len(idx)
    sl = price.iloc[s:e]
    if sl.empty:
        continue
    r = strat.generate_returns(sl, **params)
    sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
    wf_results.append(sh is not None and sh > 0)
wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
wf_pass = bool(wf_pass_fraction >= 0.75)
wf_ev = {"metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75, "n_splits": n_splits, "per_split_passed": wf_results, "note": "manual fallback split"}

from grid_test import run_strategy_grid, GridSpec
gspec = GridSpec(param_grid={"body_mult":[0.5,0.75],"reclaim_frac_min":[0.4,0.5],"reward_r_multiple":[1.5,2.0]}, symbols={"equity":["SPY"]}, vol_regime_splits=1)
res2 = run_strategy_grid(generate_returns_fn=strat.generate_returns, loader_fn_by_asset_class={"equity": load_equity}, spec=gspec, start=datetime(2019,1,1), end=datetime(2026,9,1))
pgr = {}
for c in res2.cells:
    if c.sharpe is not None:
        pgr[str(c.params)] = c.sharpe
ps_pass, ps_ev = check_parameter_sensitivity(pgr)

evidence = {
    "num_trades": num_trades,
    "sharpe": sharpe_ev, "sharpe_pass": sharpe_pass,
    "mdd": mdd_ev, "mdd_pass": mdd_pass,
    "tc": tc_ev, "tc_pass": tc_pass,
    "wf": wf_ev, "wf_pass": wf_pass,
    "ps": ps_ev, "ps_pass": ps_pass,
}
print(json.dumps(evidence, indent=2, default=str))
with open("validate_summary_piercing_line.json","w") as f:
    json.dump(evidence, f, indent=2, default=str)
