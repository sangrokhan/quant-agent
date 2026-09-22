import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.loaders import load_equity
import importlib.util
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)

spec_mod_path = "strategies/2026-09-23_tqqq_tecl_laggard_regime.py"
spec = importlib.util.spec_from_file_location("strat_tqqqtecl", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start = datetime(2016, 6, 1)
end = datetime(2026, 9, 1)

SYMBOL = "TQQQ"
price_df = load_equity(SYMBOL, start, end)
params = dict(laggard_window=3, momentum_window=126)

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
out["walk_forward"] = (bool(pf >= 0.75), {"metric": "walk_forward_pass_fraction", "value": pf, "threshold": 0.75, "n_splits": splits, "per_split_sharpe": results})

grid_cells = json.load(open("grid_cells_tqqq_tecl_laggard_regime.json"))
sym_cells = [c for c in grid_cells if c["symbol"] == SYMBOL]
param_grid_results = {}
for c in sym_cells:
    key = json.dumps(c["params"], sort_keys=True)
    param_grid_results.setdefault(key, []).append(c["sharpe"])
avg_by_param = {k: sum(v) / len(v) for k, v in param_grid_results.items()}
out["parameter_sensitivity"] = check_parameter_sensitivity(avg_by_param)

with open(f"validate_result_tqqq_tecl_laggard_{SYMBOL}.json", "w") as f:
    json.dump(out, f, indent=2, default=str)

print(json.dumps(out, indent=2, default=str))
