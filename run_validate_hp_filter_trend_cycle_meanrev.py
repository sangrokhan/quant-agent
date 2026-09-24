import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.loaders import load_equity
from validators import (
    check_sharpe_ratio,
    check_max_drawdown,
    check_transaction_cost_survival,
    check_walk_forward,
    check_parameter_sensitivity,
)
import importlib.util

spec = importlib.util.spec_from_file_location("strat_hp", "strategies/2026-09-24_hp_filter_trend_cycle_meanrev.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)
df = load_equity("QQQ", start, end)

params = dict(hp_window=40, entry_z=1.5, exit_z=0.0, max_hold_days=15, lambda_=1600.0)
ret = strat.generate_returns(df, **params)
sig = strat.generate_signals(df, **params)
num_trades = int((sig.diff().abs() == 1).sum())

results = {}
results["sharpe"] = check_sharpe_ratio(ret, min_sharpe=1.0)
results["max_drawdown"] = check_max_drawdown(ret, max_allowed_mdd=0.25)
results["tc_survival"] = check_transaction_cost_survival(ret, cost_bps_per_trade=10, num_trades=num_trades, min_net_sharpe=0.5)

# Manual walk-forward split (vbt.utils.splitting.RangeSplitter API unavailable
# in this vectorbt version -- same workaround used by other run_validate_*.py)
import vectorbt as vbt
n = len(df)
n_splits = 4
size = n // n_splits
wf_results = []
for i in range(n_splits):
    lo = i * size
    hi = n if i == n_splits - 1 else (i + 1) * size
    slice_df = df.iloc[lo:hi]
    if slice_df.empty:
        continue
    r = strat.generate_returns(slice_df, **params)
    sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
    wf_results.append(sh is not None and sh > 0)
wf_pass_fraction = sum(wf_results) / len(wf_results) if wf_results else 0.0
results["walk_forward"] = (
    bool(wf_pass_fraction >= 0.75),
    {"metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75, "n_splits": n_splits},
)

# param sensitivity from grid cell results (equity QQQ only cells)
with open("grid_cells_hp_filter_trend_cycle_meanrev.json") as f:
    cells = json.load(f)
pg = {}
for c in cells:
    if c["symbol"] == "QQQ":
        key = f"hp_window={c['params']['hp_window']},entry_z={c['params']['entry_z']}"
        pg.setdefault(key, []).append(c["sharpe"])
pg_avg = {k: sum(v)/len(v) for k, v in pg.items()}
results["param_sensitivity"] = check_parameter_sensitivity(pg_avg, max_relative_std=0.5)

out = {k: {"passed": v[0], "evidence": v[1]} for k, v in results.items()}
with open("validators_hp_filter_trend_cycle_meanrev_qqq.json", "w") as f:
    json.dump(out, f, indent=2, default=str)
print(json.dumps(out, indent=2, default=str))
print("num_trades", num_trades)
