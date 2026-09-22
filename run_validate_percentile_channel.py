import sys, os, json, functools
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.loaders import load_equity
import importlib.util
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)

spec_mod_path = "strategies/2026-09-22_percentile_channel_hysteresis.py"
spec = importlib.util.spec_from_file_location("strat_pc", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start = datetime(2018, 1, 1)
end = datetime(2026, 9, 1)

price_df = load_equity("QQQ", start, end)
params = dict(window=252, entry_threshold=0.7, exit_threshold=0.25, rebalance_days=21)

returns = strat.generate_returns(price_df, **params)
signals = strat.generate_signals(price_df, **params)
num_trades = int((signals.diff().abs() == 1).sum())

out = {}
out["sharpe_ratio"] = check_sharpe_ratio(returns)
out["max_drawdown"] = check_max_drawdown(returns)
out["transaction_cost_survival"] = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

n = len(price_df)
splits = 4
size = n // splits
results = []
import vectorbt as vbt
for i in range(splits):
    lo = i * size
    hi = n if i == splits - 1 else (i + 1) * size
    slice_df = price_df.iloc[lo:hi]
    if slice_df.empty:
        continue
    r = strat.generate_returns(slice_df, **params)
    sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
    results.append(sh)
pf = sum(1 for s in results if s and s > 0) / len(results)
out["walk_forward"] = (bool(pf >= 0.75), {"metric": "walk_forward_pass_fraction", "value": pf, "threshold": 0.75, "n_splits": splits, "per_split_sharpe": results, "note": "manual 4-equal-slice fallback"})

grid_cells = json.load(open("grid_cells_percentile_channel_hysteresis.json"))
qqq_cells = [c for c in grid_cells if c["symbol"] == "QQQ"]
param_grid_results = {}
for c in qqq_cells:
    key = json.dumps(c["params"], sort_keys=True)
    param_grid_results.setdefault(key, []).append(c["sharpe"])
avg_by_param = {k: sum(v) / len(v) for k, v in param_grid_results.items()}
out["parameter_sensitivity"] = check_parameter_sensitivity(avg_by_param)

print(json.dumps({k: [v[0], v[1]] for k, v in out.items()}, indent=2, default=str))
with open("validate_result_percentile_channel_qqq.json", "w") as f:
    json.dump({k: [v[0], v[1]] for k, v in out.items()}, f, indent=2, default=str)
