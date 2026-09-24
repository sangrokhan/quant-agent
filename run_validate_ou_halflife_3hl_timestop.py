import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival
from data.loaders import load_equity
import importlib.util

spec_mod_path = "strategies/2026-09-24_ou_halflife_3hl_timestop_sizing.py"
spec = importlib.util.spec_from_file_location("strat_ou3hl", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

results = {}
for sym in ["SPY", "QQQ"]:
    price_df = load_equity(sym, datetime(2019, 1, 1), datetime(2026, 9, 1), interval="1d")
    ret = strat.generate_returns(price_df, entry_z=2.0, time_stop_multiple=2.0)
    sharpe_ok, sharpe_ev = check_sharpe_ratio(ret)
    mdd_ok, mdd_ev = check_max_drawdown(ret)
    num_trades = int((ret.abs() > 0).astype(int).diff().abs().sum() / 2) + 1
    tc_ok, tc_ev = check_transaction_cost_survival(ret, cost_bps_per_trade=10, num_trades=num_trades)
    results[sym] = {"sharpe": sharpe_ev, "mdd": mdd_ev, "tc": tc_ev, "sharpe_pass": sharpe_ok, "mdd_pass": mdd_ok, "tc_pass": tc_ok}

print(json.dumps(results, indent=2, default=str))
with open("validate_result_ou_halflife_3hl_timestop.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
