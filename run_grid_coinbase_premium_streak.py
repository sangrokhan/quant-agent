import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validators import check_sharpe_ratio, check_max_drawdown
from data.loaders import load_crypto
import importlib.util
import pandas as pd

spec = importlib.util.spec_from_file_location("strat_cbp", "strategies/2026-09-21_coinbase_premium_streak.py")
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

SYMBOLS = ["BTC/USDT", "ETH/USDT"]
STREAK_DAYS = [3, 5, 8]
MAX_HOLD = [10, 20]

START = datetime(2018, 1, 1)
END = datetime(2026, 9, 1)

cells = []
price_cache = {}

for symbol in SYMBOLS:
    price_df = load_crypto(symbol, START, END, interval="1d")
    price_cache[symbol] = price_df
    close = price_df.set_index("timestamp")["close"] if "timestamp" in price_df.columns else price_df["close"]
    import numpy as np
    log_ret = (close / close.shift(1)).apply(lambda r: __import__("math").log(r) if r and r > 0 else None).astype(float)
    realized_vol = log_ret.rolling(20).std()
    try:
        bins = pd.qcut(realized_vol.dropna(), q=3, labels=["low", "mid", "high"], duplicates="drop")
        bins = bins.reindex(realized_vol.index)
    except ValueError:
        bins = None

    for streak_days in STREAK_DAYS:
        for max_hold in MAX_HOLD:
            params = {"binance_symbol": symbol, "streak_days": streak_days, "max_hold_days": max_hold}
            try:
                full_returns = strat.generate_returns(price_df, **params)
            except Exception as exc:
                cells.append({"params": params, "symbol": symbol, "vol_regime": "n/a", "sharpe": None, "sharpe_passed": False, "mdd": None, "mdd_passed": False, "error": str(exc)})
                continue

            if bins is None:
                regime_masks = {"all": pd.Series(True, index=close.index)}
            else:
                regime_masks = {}
                for label in ["low", "mid", "high"]:
                    regime_masks[label] = (bins == label).fillna(False)

            for regime_label, mask in regime_masks.items():
                mask = mask.reindex(full_returns.index).fillna(False)
                sliced = full_returns[mask]
                if sliced.empty or sliced.abs().sum() == 0:
                    cells.append({"params": params, "symbol": symbol, "vol_regime": regime_label, "sharpe": None, "sharpe_passed": False, "mdd": None, "mdd_passed": False, "error": "empty/no-trade slice"})
                    continue
                try:
                    sharpe_passed, sharpe_ev = check_sharpe_ratio(sliced, min_sharpe=1.0)
                    mdd_passed, mdd_ev = check_max_drawdown(sliced, max_allowed_mdd=0.25)
                    cells.append({
                        "params": params, "symbol": symbol, "vol_regime": regime_label,
                        "sharpe": sharpe_ev.get("value"), "sharpe_passed": sharpe_passed,
                        "mdd": mdd_ev.get("value"), "mdd_passed": mdd_passed, "error": None,
                    })
                except Exception as exc:
                    cells.append({"params": params, "symbol": symbol, "vol_regime": regime_label, "sharpe": None, "sharpe_passed": False, "mdd": None, "mdd_passed": False, "error": str(exc)})

total = len(cells)
passed = sum(1 for c in cells if c["error"] is None and c["sharpe_passed"] and c["mdd_passed"])
by_symbol = {}
by_regime = {}
for c in cells:
    bs = by_symbol.setdefault(c["symbol"], {"passed": 0, "total": 0})
    bs["total"] += 1
    bs["passed"] += int(c["error"] is None and c["sharpe_passed"] and c["mdd_passed"])
    br = by_regime.setdefault(c["vol_regime"], {"passed": 0, "total": 0})
    br["total"] += 1
    br["passed"] += int(c["error"] is None and c["sharpe_passed"] and c["mdd_passed"])

valid_cells = [c for c in cells if c["sharpe"] is not None]
best = max(valid_cells, key=lambda c: c["sharpe"]) if valid_cells else None
worst = min(valid_cells, key=lambda c: c["sharpe"]) if valid_cells else None

summary = {
    "metric": "grid_test_coinbase_premium",
    "total_cells": total,
    "passed_cells": passed,
    "pass_fraction": (passed / total) if total else 0.0,
    "by_symbol": by_symbol,
    "by_vol_regime": by_regime,
    "best_cell": best,
    "worst_cell": worst,
}

with open("grid_summary_coinbase_premium_streak.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
with open("grid_cells_coinbase_premium_streak.json", "w") as f:
    json.dump(cells, f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str))
