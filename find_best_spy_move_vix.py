import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))

from validators import check_sharpe_ratio, check_max_drawdown
from data.loaders import load_equity
import importlib.util

spec_mod_path = "strategies/2026-09-24_move_vix_divergence_regime_gate.py"
spec = importlib.util.spec_from_file_location("strat_movevix", spec_mod_path)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

price_df = load_equity("SPY", datetime(2019, 1, 1), datetime(2026, 9, 1), interval="1d")

results = []
for dt in [0.75, 1.0, 1.25, 1.5, 2.0]:
    for sw in [50, 75, 100, 150, 200]:
        for zw in [42, 63, 90, 126]:
            for mh in [20, 40, 60]:
                r = strat.generate_returns(price_df, divergence_threshold=dt, sma_window=sw, zscore_window=zw, max_hold_days=mh)
                sok, sev = check_sharpe_ratio(r)
                mok, mev = check_max_drawdown(r)
                if sok and mok:
                    results.append({"dt": dt, "sw": sw, "zw": zw, "mh": mh, "sharpe": sev["value"], "mdd": mev["value"]})

results.sort(key=lambda x: -x["sharpe"])
print(json.dumps(results[:15], indent=2))
with open("spy_move_vix_wide_search.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\ntotal passing combos: {len(results)} / 300")
