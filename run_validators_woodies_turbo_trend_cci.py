import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.loaders import load_equity
import importlib.util
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)
import vectorbt as vbt

spec_mod_path = "strategies/2026-09-27_woodies_turbo_trend_cci_crossover.py"
spec = importlib.util.spec_from_file_location("strat_woodie", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

BEST_PARAMS = dict(turbo_period=9, trend_period=20, trend_established_bars=4, max_hold_days=20)
start = datetime(2018, 1, 1)
end = datetime(2026, 9, 1)

grid_cells = json.load(open("grid_cells_woodies_turbo_trend_cci.json"))

results = {}
for symbol in ["QQQ", "SPY"]:
    price_df = load_equity(symbol, start, end)
    returns = strat.generate_returns(price_df, **BEST_PARAMS)
    pos = strat.generate_signals(price_df, **BEST_PARAMS)
    num_trades = int((pos.diff().abs() == 1).sum())

    sharpe_out = check_sharpe_ratio(returns, min_sharpe=1.0)
    mdd_out = check_max_drawdown(returns, max_allowed_mdd=0.25)
    tc_out = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)

    n = len(price_df)
    splits = 4
    size = n // splits
    wf_results = []
    for i in range(splits):
        lo = i * size
        hi = n if i == splits - 1 else (i + 1) * size
        slice_df = price_df.iloc[lo:hi]
        if slice_df.empty:
            continue
        r = strat.generate_returns(slice_df, **BEST_PARAMS)
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        wf_results.append(sh)
    pf = sum(1 for s in wf_results if s and s > 0) / len(wf_results)
    wf_out = (bool(pf >= 0.75), {"metric": "walk_forward_pass_fraction", "value": pf, "threshold": 0.75, "n_splits": splits, "per_split_sharpe": wf_results})

    sym_cells = [c for c in grid_cells if c["symbol"] == symbol]
    param_grid_results = {}
    for c in sym_cells:
        key = json.dumps(c["params"], sort_keys=True)
        if c["sharpe"] is not None:
            param_grid_results.setdefault(key, []).append(c["sharpe"])
    avg_by_param = {k: sum(v) / len(v) for k, v in param_grid_results.items()}
    ps_out = check_parameter_sensitivity(avg_by_param)

    all_pass = sharpe_out[0] and mdd_out[0] and tc_out[0] and wf_out[0] and ps_out[0]
    results[symbol] = {
        "num_trades": num_trades,
        "sharpe": sharpe_out,
        "mdd": mdd_out,
        "tc": tc_out,
        "wf": wf_out,
        "param_sensitivity": ps_out,
        "all_pass": all_pass,
    }

with open("validators_woodies_turbo_trend_cci.json", "w") as f:
    json.dump(results, f, indent=2, default=str)

print(json.dumps(results, indent=2, default=str))
