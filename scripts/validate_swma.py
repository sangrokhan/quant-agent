import sys, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
import importlib.util
from datetime import datetime

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-21_sine_weighted_ma_crossover.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_equity
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)
import vectorbt as vbt

start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)
symbol = "QQQ"
best_params = {"fast_window": 10, "slow_window": 30, "trend_window": 100}

df = load_equity(symbol, start, end)
returns = strat.generate_returns(df, **best_params)

results = {}
passed, ev = check_sharpe_ratio(returns, min_sharpe=1.0)
results["sharpe_ratio"] = ev
print("sharpe:", passed, ev)

passed, ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
results["max_drawdown"] = ev
print("mdd:", passed, ev)

position = strat.generate_signals(df, **best_params)
num_trades = int((position.diff().abs() == 1).sum())
passed, ev = check_transaction_cost_survival(returns, cost_bps_per_trade=5.0, num_trades=num_trades, min_net_sharpe=0.5)
results["transaction_cost_survival"] = ev
print("tc survival:", passed, ev, "trades=", num_trades)

n = len(df)
chunk = n // 4
wf_results = []
for i in range(4):
    lo, hi = i*chunk, (i+1)*chunk if i < 3 else n
    slice_df = df.iloc[lo:hi]
    r = strat.generate_returns(slice_df, **best_params)
    sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
    wf_results.append(bool(sh is not None and sh > 0))
wf_pass_fraction = sum(wf_results)/len(wf_results)
results["walk_forward"] = {"metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75, "per_split_passed": wf_results}
print("walk forward:", wf_pass_fraction >= 0.75, results["walk_forward"])

grid_results = {}
for fw in [10, 20]:
    for sw in [30, 50]:
        r = strat.generate_returns(df, fast_window=fw, slow_window=sw, trend_window=100)
        sh = r.vbt.returns(freq="D").sharpe_ratio()
        grid_results[f"fw={fw},sw={sw}"] = float(sh) if sh is not None else 0.0
passed, ev = check_parameter_sensitivity(grid_results, max_relative_std=0.5)
results["parameter_sensitivity"] = ev
print("param sensitivity:", passed, ev)

with open("/tmp/swma_validators.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print(json.dumps(results, indent=2, default=str))
