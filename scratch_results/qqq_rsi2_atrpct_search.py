import importlib.util
import sys
import json
from datetime import datetime

sys.path.insert(0, "data")
sys.path.insert(0, "validation")

spec = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-20_rsi2_atrpct_lowvol_gate.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

import vectorbt as vbt  # noqa: F401,E402
from loaders import load_equity  # noqa: E402

start = datetime(2016, 1, 1)
end = datetime(2026, 9, 1)

price_df = load_equity("QQQ", start, end)

# Local search around the QQQ near-miss: vary entry/exit/hold/atr params
best = None
results = []
for et in [3.0, 5.0, 7.0, 10.0]:
    for xt in [55.0, 60.0, 65.0, 70.0]:
        for mh in [7, 10, 15]:
            for alb in [63, 100, 150]:
                r = strat.generate_returns(price_df, entry_threshold=et, exit_threshold=xt, max_hold_days=mh, atr_lookback=alb)
                sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
                if sh is not None:
                    results.append({"et": et, "xt": xt, "mh": mh, "alb": alb, "sharpe": float(sh)})

results.sort(key=lambda x: -x["sharpe"])
print(json.dumps(results[:15], indent=2))
with open("scratch_results/qqq_rsi2_atrpct_search.json", "w") as f:
    json.dump(results[:15], f, indent=2)
