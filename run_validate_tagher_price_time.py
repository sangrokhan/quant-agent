import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))

from datetime import datetime
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "tagher_strat",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies", "2026-09-12_tagher_price_time_filter.py"),
)
strat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(strat)
from loaders import load_equity
from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)

start, end = datetime(2018, 1, 1), datetime(2026, 9, 1)
best_params = dict(trend_sma_window=50)

report = {}
for symbol in ["SPY", "QQQ"]:
    price_df = load_equity(symbol, start, end)
    returns = strat.generate_returns(price_df, **best_params)
    positions = strat.generate_signals(price_df, **best_params)
    num_trades = int((positions.diff() == 1).sum())

    sharpe_p, sharpe_e = check_sharpe_ratio(returns)
    mdd_p, mdd_e = check_max_drawdown(returns)
    tc_p, tc_e = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades)

    sens_grid = {}
    for tw in [0, 50, 100, 150, 200]:
        r = strat.generate_returns(price_df, trend_sma_window=tw)
        import vectorbt as vbt
        sh = r.vbt.returns(freq="D").sharpe_ratio()
        sens_grid[str(tw)] = float(sh) if sh is not None else 0.0
    sens_p, sens_e = check_parameter_sensitivity(sens_grid)

    report[symbol] = {
        "num_trades": num_trades,
        "sharpe": {"passed": sharpe_p, **sharpe_e},
        "max_drawdown": {"passed": mdd_p, **mdd_e},
        "transaction_cost_survival": {"passed": tc_p, **tc_e},
        "parameter_sensitivity": {"passed": sens_p, **sens_e},
    }

with open("validators_tagher_price_time.json", "w") as f:
    json.dump(report, f, indent=2, default=str)
print(json.dumps(report, indent=2, default=str))
