import sys, os, json, itertools
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

import importlib.util
spec_mod = importlib.util.spec_from_file_location(
    "gsr", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-20_gold_silver_ratio_rsi5_gld.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

from loaders import load_equity
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity

df = load_equity("GLD", start=datetime(2018, 1, 1), end=datetime(2026, 9, 1))
params = dict(rsi_period=5, rsi_entry=75.0, rsi_exit=30.0)

r = strat.generate_returns(df, **params)
pos = strat.generate_signals(df, **params)
num_trades = int((pos.diff().abs() > 0).sum())

sh_pass, sh_ev = check_sharpe_ratio(r)
mdd_pass, mdd_ev = check_max_drawdown(r)
tc_pass, tc_ev = check_transaction_cost_survival(r, cost_bps_per_trade=5.0, num_trades=num_trades)

n_splits = 4
idx = df.index
chunk_bounds = [int(i * len(idx) / n_splits) for i in range(n_splits + 1)]
wf_results = []
for i in range(n_splits):
    lo, hi = chunk_bounds[i], chunk_bounds[i + 1]
    slice_df = df.iloc[lo:hi]
    if slice_df.empty:
        continue
    rr = strat.generate_returns(slice_df, **params)
    sh = rr.vbt.returns(freq="D").sharpe_ratio() if len(rr) else None
    wf_results.append(sh is not None and sh > 0)
wf_pass_fraction = (sum(wf_results) / len(wf_results)) if wf_results else 0.0
wf_pass = wf_pass_fraction >= 0.75
wf_ev = {
    "metric": "walk_forward_pass_fraction_manual",
    "value": wf_pass_fraction,
    "threshold": 0.75,
    "n_splits": n_splits,
    "per_split_passed": wf_results,
    "note": "manual split used -- validators.check_walk_forward errors on installed vectorbt (vbt.utils.splitting missing)",
}

# parameter sensitivity: sweep neighboring rsi_entry/rsi_exit values
sweep = {}
for entry_v, exit_v in itertools.product([70.0, 75.0, 80.0], [25.0, 30.0, 35.0]):
    p = dict(rsi_period=5, rsi_entry=entry_v, rsi_exit=exit_v)
    rr = strat.generate_returns(df, **p)
    sh = check_sharpe_ratio(rr)[1]["value"]
    sweep[str(p)] = sh if sh is not None else 0.0

ps_pass, ps_ev = check_parameter_sensitivity(sweep)

result = {
    "sharpe": {"passed": sh_pass, **sh_ev},
    "max_drawdown": {"passed": mdd_pass, **mdd_ev},
    "transaction_cost_survival": {"passed": tc_pass, **tc_ev},
    "walk_forward": {"passed": wf_pass, **wf_ev},
    "parameter_sensitivity": {"passed": ps_pass, **ps_ev},
    "num_trades": num_trades,
}
print(json.dumps(result, indent=2, default=str))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validators_gold_silver_ratio_rsi5.json"), "w") as f:
    json.dump(result, f, indent=2, default=str)
