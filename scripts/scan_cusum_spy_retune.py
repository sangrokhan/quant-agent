import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies"))

import importlib.util
import itertools
import vectorbt as vbt  # noqa: F401
from loaders import load_equity

spec_mod = importlib.util.spec_from_file_location(
    "strat", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategies", "2026-09-10_cusum_filter_trend_event.py")
)
strat = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(strat)

start, end = datetime(2018, 1, 1), datetime(2026, 9, 1)
price_df = load_equity("SPY", start, end)

results = {}
best = None
best_sharpe = -999
for vol_window, h_mult, max_hold_days in itertools.product([10, 20, 40, 60], [2.0, 3.0, 4.0, 5.0, 6.0], [15, 30, 45]):
    params = dict(vol_window=vol_window, h_mult=h_mult, max_hold_days=max_hold_days)
    r = strat.generate_returns(price_df, **params)
    sh = r.vbt.returns(freq="D").sharpe_ratio()
    if sh is None:
        continue
    results[str(params)] = float(sh)
    if sh > best_sharpe:
        best_sharpe = sh
        best = params

print("BEST SPY config:", best, "sharpe:", best_sharpe)
top10 = sorted(results.items(), key=lambda x: -x[1])[:10]
print(json.dumps(top10, indent=2))

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cusum_spy_retune_scan.json"), "w") as f:
    json.dump({"best": best, "best_sharpe": best_sharpe, "top10": top10}, f, indent=2, default=str)
