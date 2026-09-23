import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.loaders import load_equity, load_crypto
import importlib.util
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_walk_forward, check_parameter_sensitivity,
)

spec_mod_path = "strategies/2026-09-24_qstick_zeroline_cross.py"
spec = importlib.util.spec_from_file_location("strat_qs", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start = datetime(2019, 1, 1)
end = datetime(2026, 9, 1)

SYMBOL = sys.argv[1] if len(sys.argv) > 1 else "QQQ"
ASSET_CLASS = sys.argv[2] if len(sys.argv) > 2 else "equity"
PARAMS_JSON = sys.argv[3] if len(sys.argv) > 3 else None

if ASSET_CLASS == "crypto":
    price_df = load_crypto(SYMBOL, start, end, interval="1d")
else:
    price_df = load_equity(SYMBOL, start, end)

if PARAMS_JSON:
    params = json.loads(PARAMS_JSON)
else:
    params = dict(qstick_period=14, ema_period=50, rsi_overbought_guard=70)

returns = strat.generate_returns(price_df, **params)
sig_params = {k: v for k, v in params.items() if k != "leverage_cap"}
signals = strat.generate_signals(price_df, **sig_params)
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
out["walk_forward"] = (bool(pf >= 0.75), {"metric": "walk_forward_pass_fraction", "value": pf, "threshold": 0.75, "n_splits": splits, "per_split_sharpe": results})

grid_cells = json.load(open("grid_cells_qstick_zeroline_cross.json"))
sym_cells = [c for c in grid_cells if c["symbol"] == SYMBOL]
param_grid_results = {}
for c in sym_cells:
    key = json.dumps(c["params"], sort_keys=True)
    param_grid_results.setdefault(key, []).append(c["sharpe"])
avg_by_param = {k: sum(v) / len(v) for k, v in param_grid_results.items()}
out["parameter_sensitivity"] = check_parameter_sensitivity(avg_by_param)

print(json.dumps({k: [v[0], v[1]] for k, v in out.items()}, indent=2, default=str))
symname = SYMBOL.replace("/", "_")
with open(f"validate_result_qstick_zeroline_cross_{symname}.json", "w") as f:
    json.dump({k: [v[0], v[1]] for k, v in out.items()}, f, indent=2, default=str)
