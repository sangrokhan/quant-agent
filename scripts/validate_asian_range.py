import sys, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
import importlib.util
from datetime import datetime
import numpy as np

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-21_asian_range_london_breakout.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_crypto
from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity
import vectorbt as vbt

start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)
symbol = "ETH/USDT"
best_params = {"asian_end_hour": 6, "breakout_pct": 0.002, "max_hold_bars": 4}

df = load_crypto(symbol, start, end)
returns = strat.generate_returns(df, **best_params)

results = {}
passed, ev = check_sharpe_ratio(returns, min_sharpe=1.0, periods_per_year=24*365)
results["sharpe_ratio"] = ev
print("sharpe:", passed, ev)

passed, ev = check_max_drawdown(returns, max_allowed_mdd=0.25)
results["max_drawdown"] = ev
print("mdd:", passed, ev)

position = strat.generate_signals(df, **best_params)
num_trades = int((position.diff().abs() == 1).sum())
passed, ev = check_transaction_cost_survival(returns, cost_bps_per_trade=5.0, num_trades=num_trades, min_net_sharpe=0.5)
results["transaction_cost_survival"] = ev
print("tc survival:", passed, ev, "num_trades=", num_trades)

# manual walk-forward: 4 contiguous chunks
n = len(df)
chunk = n // 4
wf_results = []
for i in range(4):
    lo, hi = i*chunk, (i+1)*chunk if i < 3 else n
    slice_df = df.iloc[lo:hi]
    r = strat.generate_returns(slice_df, **best_params)
    sh = r.vbt.returns(freq="H").sharpe_ratio() if len(r) else None
    wf_results.append(bool(sh is not None and sh > 0))
wf_pass_fraction = sum(wf_results)/len(wf_results)
results["walk_forward"] = {"metric": "walk_forward_pass_fraction", "value": wf_pass_fraction, "threshold": 0.75, "per_split_passed": wf_results}
print("walk forward:", wf_pass_fraction >= 0.75, results["walk_forward"])

grid_results = {}
for bp in [0.0, 0.002, 0.005]:
    r = strat.generate_returns(df, asian_end_hour=6, breakout_pct=bp, max_hold_bars=4)
    sh = r.vbt.returns(freq="H").sharpe_ratio()
    grid_results[f"breakout_pct={bp}"] = float(sh) if sh is not None else 0.0
passed, ev = check_parameter_sensitivity(grid_results, max_relative_std=0.5)
results["parameter_sensitivity"] = ev
print("param sensitivity:", passed, ev)

with open("/tmp/asian_range_validators.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print(json.dumps(results, indent=2, default=str))
