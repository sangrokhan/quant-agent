"""Strategy: Positive Volume Index (PVI) 255-day SMA crossover (Fosback bull/bear filter).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-063):
Per the Google AI overview summarizing Norman Fosback's classic PVI rule
(https://www.google.com/search?q=Positive+Volume+Index+PVI+Quantified+Strategies+trading+rules,
read via browser_exec this iteration -- web_search's DDGS backend
intermittently TLS-erroring, and both quantifiedstrategies.com and
arrowalgo.com's PVI-specific article URLs 404'd), the Positive Volume Index
(PVI) is a cumulative index that only updates its percentage price change
on days when volume rises versus the prior day (crowd/retail-driven
participation days), left unchanged otherwise. Fosback's original rule:
"Go long only when the PVI is above its 255-day SMA" (bull-market regime
filter, ~1 trading year), "exit to cash when PVI falls below its 255-day
SMA" (bear-market/defensive filter). First PVI-indicator test in this repo
(0 prior KB hits for "on balance volume"-adjacent "PVI"/"Positive Volume
Index" specifically, though NVI has 2-3 prior mentions as a companion
concept never itself tested as the primary signal).

Signal logic
------------
- Compute PVI: starts at 100 (or 1.0), on each bar where volume > prior
  volume, PVI *= (1 + close.pct_change()); on other bars PVI stays
  unchanged (per Fosback's definition -- this is a cumulative index, not
  reset each period).
- Long entry / hold: PVI > SMA(pvi_sma_window) of PVI itself (bull filter).
- Exit to flat: PVI < SMA(pvi_sma_window) of PVI itself (bear filter).
- No time-stop -- this is a slow, regime-following macro filter by design
  (per source, using a full trading year's SMA), consistent with Fosback's
  original monthly-rebalance-style intent; we evaluate it daily here but
  keep the same slow SMA window.
- Flat otherwise. Long-only (no short per SAFETY.md scope).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _pvi(close: pd.Series, volume: pd.Series) -> pd.Series:
    pvi = pd.Series(index=close.index, dtype=float)
    pvi.iloc[0] = 100.0
    pct_change = close.pct_change()
    vol_rising = volume > volume.shift(1)
    for i in range(1, len(close)):
        prev = pvi.iloc[i - 1]
        if bool(vol_rising.iloc[i]) and pd.notna(pct_change.iloc[i]):
            pvi.iloc[i] = prev * (1.0 + pct_change.iloc[i])
        else:
            pvi.iloc[i] = prev
    return pvi


def generate_signals(
    price_df: pd.DataFrame,
    pvi_sma_window: int = 255,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    pvi = _pvi(close, volume)
    pvi_sma = pvi.rolling(pvi_sma_window).mean()

    bull = (pvi > pvi_sma).fillna(False)
    position = bull.astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    pvi_sma_window: int = 255,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(df, pvi_sma_window=pvi_sma_window)
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
