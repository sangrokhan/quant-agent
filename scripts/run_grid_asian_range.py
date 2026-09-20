import sys, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "data")
import importlib.util
from datetime import datetime
import numpy as np
import pandas as pd
import vectorbt as vbt

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-21_asian_range_london_breakout.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_crypto

start, end = datetime(2019, 1, 1), datetime(2026, 9, 1)
symbols = ["BTC/USDT", "ETH/USDT"]
param_grid = {
    "asian_end_hour": [6, 8],
    "breakout_pct": [0.0, 0.002, 0.005],
    "max_hold_bars": [4, 8],
}

import itertools
combos = list(itertools.product(*param_grid.values()))
keys = list(param_grid.keys())

results = []
price_cache = {}
for sym in symbols:
    price_cache[sym] = load_crypto(sym, start, end)

for sym in symbols:
    df = price_cache[sym]
    # realized vol terciles based on rolling 24h vol
    ret = df["close"].pct_change()
    roll_vol = ret.rolling(24*7).std()
    terciles = roll_vol.quantile([0.33, 0.66])
    low_mask = roll_vol <= terciles.iloc[0]
    high_mask = roll_vol >= terciles.iloc[1]
    mid_mask = ~low_mask & ~high_mask

    for combo in combos:
        params = dict(zip(keys, combo))
        r = strat.generate_returns(df, **params)
        full_sh = r.vbt.returns(freq="H").sharpe_ratio()
        cell = {"symbol": sym, **params, "full_sample_sharpe": float(full_sh) if full_sh is not None and not np.isnan(full_sh) else None}
        for label, mask in [("low", low_mask), ("mid", mid_mask), ("high", high_mask)]:
            mask_aligned = mask.reindex(r.index).fillna(False)
            sliced = r[mask_aligned]
            if sliced.abs().sum() == 0 or len(sliced) < 10:
                cell[f"sharpe_{label}"] = None
            else:
                sh = sliced.vbt.returns(freq="H").sharpe_ratio()
                cell[f"sharpe_{label}"] = float(sh) if sh is not None and not np.isnan(sh) else None
        results.append(cell)

total = len(results)
passed = sum(1 for c in results if c["full_sample_sharpe"] is not None and c["full_sample_sharpe"] >= 1.0)
by_symbol = {}
for c in results:
    d = by_symbol.setdefault(c["symbol"], {"passed":0,"total":0})
    d["total"] += 1
    if c["full_sample_sharpe"] is not None and c["full_sample_sharpe"] >= 1.0:
        d["passed"] += 1

best = max(results, key=lambda c: c["full_sample_sharpe"] if c["full_sample_sharpe"] is not None else -999)
worst = min(results, key=lambda c: c["full_sample_sharpe"] if c["full_sample_sharpe"] is not None else 999)

summary = {
    "metric": "manual_hourly_grid (grid_test.py incompatible -- forces daily bars)",
    "total_cells": total,
    "passed_cells": passed,
    "pass_fraction": passed/total,
    "by_symbol": by_symbol,
    "best_cell": best,
    "worst_cell": worst,
}
print(json.dumps(summary, indent=2, default=str))
with open("/tmp/asian_range_grid.json", "w") as f:
    json.dump({"summary": summary, "all_cells": results}, f, indent=2, default=str)
