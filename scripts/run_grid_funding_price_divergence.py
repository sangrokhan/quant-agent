import sys, os, json
sys.path.insert(0, "strategies")
sys.path.insert(0, "validation")
sys.path.insert(0, "data")
sys.path.insert(0, ".")
from datetime import datetime
import importlib.util
import numpy as np
import pandas as pd

spec = importlib.util.spec_from_file_location("strat_mod", "strategies/2026-09-23_funding_rate_price_divergence_reversal.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

from loaders import load_crypto
from validators import check_sharpe_ratio, check_max_drawdown

START = datetime(2020, 1, 1)
END = datetime(2026, 9, 1)

def vol_regime_labels(price_df, n=3):
    ret = price_df["close"].pct_change()
    rv = ret.rolling(20).std()
    q = rv.rank(pct=True)
    labels = pd.cut(q, bins=[0, 1/3, 2/3, 1.0], labels=["low", "mid", "high"], include_lowest=True)
    return labels

results = {}
all_cells = []
for sym in ["BTC/USDT", "ETH/USDT"]:
    price_df = load_crypto(sym, START, END, interval="1d")
    vol_labels = vol_regime_labels(price_df)
    cells = []
    for divergence_window in [5, 10, 20]:
        for funding_window in [14, 21]:
            for max_hold_days in [20, 30]:
                params = dict(symbol=sym, divergence_window=divergence_window, funding_window=funding_window, max_hold_days=max_hold_days)
                returns = strat.generate_returns(price_df, **params)
                sh_pass, sh_ev = check_sharpe_ratio(returns)
                mdd_pass, mdd_ev = check_max_drawdown(returns)
                overall = {"symbol": sym, "params": params, "sharpe": sh_ev["value"], "sharpe_passed": sh_pass,
                           "mdd": mdd_ev["value"], "mdd_passed": mdd_pass, "passed": sh_pass and mdd_pass}
                # per vol-regime breakdown
                regime_res = {}
                for label in ["low", "mid", "high"]:
                    mask = (vol_labels == label).reindex(returns.index).fillna(False)
                    sub_ret = returns.where(mask, 0.0)
                    if sub_ret.abs().sum() == 0:
                        regime_res[label] = {"sharpe": None, "passed": False}
                        continue
                    sh_p, sh_e = check_sharpe_ratio(sub_ret)
                    md_p, md_e = check_max_drawdown(sub_ret)
                    regime_res[label] = {"sharpe": sh_e["value"], "passed": sh_p and md_p}
                overall["by_vol_regime"] = regime_res
                cells.append(overall)
                all_cells.append(overall)
    results[sym] = cells
    passed = sum(1 for c in cells if c["passed"])
    print(sym, "pass_fraction", passed, "/", len(cells))
    for c in cells:
        print("  ", c["params"]["divergence_window"], c["params"]["funding_window"], c["params"]["max_hold_days"],
              round(c["sharpe"],3) if c["sharpe"] else None, round(c["mdd"],3) if c["mdd"] else None, c["passed"])

total = len(all_cells)
passed_total = sum(1 for c in all_cells if c["passed"])
print("TOTAL pass_fraction", passed_total, "/", total)

with open("grid_cells_funding_price_divergence.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
