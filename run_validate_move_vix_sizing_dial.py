import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))

from validators import check_sharpe_ratio, check_max_drawdown, check_transaction_cost_survival, check_parameter_sensitivity
from data.loaders import load_equity
import importlib.util

spec_mod_path = "strategies/2026-09-24_move_vix_divergence_sizing_dial.py"
spec = importlib.util.spec_from_file_location("strat_movevixdial", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

CFG = {"dial_scale": 2.0, "sma_window": 50}

results = {}
for sym in ["SPY", "QQQ"]:
    price_df = load_equity(sym, datetime(2019, 1, 1), datetime(2026, 9, 1), interval="1d")
    ret = strat.generate_returns(price_df, **CFG)
    sok, sev = check_sharpe_ratio(ret)
    mok, mev = check_max_drawdown(ret)
    num_trades = int((ret.abs() > 0).astype(int).diff().abs().sum() / 2) + 1
    tok, tev = check_transaction_cost_survival(ret, cost_bps_per_trade=10, num_trades=num_trades)
    results[sym] = {"sharpe": sev, "mdd": mev, "tc": tev, "sharpe_pass": sok, "mdd_pass": mok, "tc_pass": tok, "num_trades": num_trades}

print(json.dumps(results, indent=2, default=str))
with open("validate_result_move_vix_sizing_dial.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
