import importlib.util
import sys
import json
from datetime import datetime

sys.path.insert(0, "data")
sys.path.insert(0, "validation")

spec = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-18_four_up_days_hold_to_friday.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

import vectorbt as vbt  # noqa: F401,E402
from loaders import load_equity  # noqa: E402
from validators import (
    check_sharpe_ratio,
    check_max_drawdown,
    check_transaction_cost_survival,
    check_parameter_sensitivity,
)  # noqa: E402

start = datetime(2016, 1, 1)
end = datetime(2026, 9, 1)

results = {}
for symbol in ["QQQ", "SPY"]:
    price_df = load_equity(symbol, start, end)
    for streak_len in [4, 5]:
        params = {"streak_len": streak_len}
        r = strat.generate_returns(price_df, **params)
        sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
        results.setdefault(symbol, {})[streak_len] = float(sh) if sh is not None else None

print(json.dumps(results, indent=2, default=str))
