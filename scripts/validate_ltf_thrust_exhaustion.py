import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies"))

from validators import (
    check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival,
    check_parameter_sensitivity,
)
from loaders import load_equity
import importlib.util

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-27_ltf_thrust_exhaustion_reversal.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

price_df = load_equity("SPY", start=datetime(2015, 1, 1), end=datetime(2026, 9, 1))

best_params = dict(thrust_body_atr_mult=1.2, exhaustion_body_frac=0.5, confirm_window=2)
returns = strat.generate_returns(price_df, **best_params)
signals = strat.generate_signals(price_df, **best_params)
num_trades = int((signals.diff() == 1).sum())

sharpe_p, sharpe_e = check_sharpe_ratio(returns, min_sharpe=1.0)
mdd_p, mdd_e = check_max_drawdown(returns, max_allowed_mdd=0.25)
tc_p, tc_e = check_transaction_cost_survival(returns, cost_bps_per_trade=10.0, num_trades=num_trades, min_net_sharpe=0.5)

sens_grid = {}
for tb in [1.0, 1.2, 1.5]:
    for eb in [0.3, 0.4, 0.5]:
        p = dict(thrust_body_atr_mult=tb, exhaustion_body_frac=eb, confirm_window=2)
        r = strat.generate_returns(price_df, **p)
        import vectorbt as vbt
        sh = r.vbt.returns(freq="D").sharpe_ratio()
        sens_grid[str(p)] = float(sh) if sh is not None else 0.0

sens_p, sens_e = check_parameter_sensitivity(sens_grid, max_relative_std=0.5)

result = {
    "symbol": "SPY",
    "best_params": best_params,
    "num_trades": num_trades,
    "sharpe": {"passed": sharpe_p, **sharpe_e},
    "max_drawdown": {"passed": mdd_p, **mdd_e},
    "tc_survival": {"passed": tc_p, **tc_e},
    "parameter_sensitivity": {"passed": sens_p, **sens_e},
}
print(json.dumps(result, indent=2, default=str))

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validate_result_ltf_thrust_exhaustion.json"), "w") as f:
    json.dump(result, f, indent=2, default=str)
