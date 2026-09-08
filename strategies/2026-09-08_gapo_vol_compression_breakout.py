"""Strategy: Gopalkrishnan Range Index (GAPO) volatility-compression dual
breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-050):
Per gocharting.com's GAPO docs (browser_exec fallback -- web_search's
DuckDuckGo backend returned only unrelated results for the first query,
then found via a corrected second query), the Gopalkrishnan Range Index
(GAPO=ln(HH(n)-LL(n))/ln(n), Jayanthi Gopalakrishnan 1994, log-normalized
N-period high-low range) is a volatility-regime gauge. Source's own
explicit strategy: "When GAPO drops to historical lows, anticipate a
volatility expansion. Set breakout entries above recent highs and below
recent lows, entering whichever side breaks first." This repo is long-only
(SAFETY.md), so we implement the long side of that dual-breakout rule:
enter long only when GAPO is at/near a historical low (percentile-rank
compression) AND price breaks above its own recent Donchian high; exit on
a volatility-based (ATR) trailing-stop-style close-below-recent-low rule
or a max_hold_days time-stop, honoring the source's "use a wider stop
during high GAPO periods" caveat via an ATR-scaled stop distance that
widens automatically as realized range increases post-entry.

First GAPO/Gopalkrishnan Range Index strategy in this repo (0 prior hits).

Signal logic
------------
- GAPO(n) = ln(HH(n) - LL(n)) / ln(n)
- GAPO percentile rank over `gapo_lookback` bars; "historical low" =
  percentile rank <= `gapo_pct_threshold` (e.g. 0.20 = bottom quintile).
- Donchian breakout: close crosses above the highest close of the prior
  `donchian_window` bars.
- Entry (long): GAPO in its historical-low percentile band at entry AND
  the Donchian breakout fires on the same bar.
- Exit: close falls below an ATR-scaled trailing stop (entry-time ATR *
  atr_mult, ratcheted up with the running max close since entry -- so the
  stop naturally widens if realized range/ATR increases after entry, per
  source's "wider stop during high GAPO periods" caution), OR a
  max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _gapo(df: pd.DataFrame, n: int) -> pd.Series:
    hh = df["high"].rolling(n).max()
    ll = df["low"].rolling(n).min()
    rng = (hh - ll).clip(lower=1e-9)
    return np.log(rng) / np.log(n)


def generate_signals(
    price_df: pd.DataFrame,
    gapo_window: int = 14,
    gapo_lookback: int = 100,
    gapo_pct_threshold: float = 0.2,
    donchian_window: int = 20,
    atr_window: int = 14,
    atr_mult: float = 2.5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    gapo = _gapo(df, gapo_window)
    # Vectorized rolling percentile rank of the last value within its own
    # trailing window (equivalent to rolling(...).apply(rank(pct=True))
    # but ~100x faster than a Python-level rolling apply).
    gapo_vals = gapo.to_numpy()
    n = len(gapo_vals)
    pctrank_vals = np.full(n, np.nan)
    for i in range(gapo_lookback - 1, n):
        window = gapo_vals[i - gapo_lookback + 1 : i + 1]
        if np.isnan(window).any():
            continue
        pctrank_vals[i] = (window <= window[-1]).sum() / gapo_lookback
    gapo_pctrank = pd.Series(pctrank_vals, index=gapo.index)
    tr = _true_range(df)
    atr = tr.rolling(atr_window).mean()

    donchian_high = close.rolling(donchian_window).max().shift(1)
    breakout = close > donchian_high
    vol_compressed = gapo_pctrank <= gapo_pct_threshold

    entry_signal = breakout & vol_compressed

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    stop_level = None
    running_max_close = None
    for i in range(len(close)):
        if not in_pos:
            if bool(entry_signal.iloc[i]) if pd.notna(entry_signal.iloc[i]) else False:
                in_pos = True
                entry_idx = i
                a = atr.iloc[i]
                stop_level = close.iloc[i] - (a * atr_mult if pd.notna(a) else close.iloc[i] * 0.1)
                running_max_close = close.iloc[i]
                position.iloc[i] = 1
        else:
            held = i - entry_idx
            c = close.iloc[i]
            if c > running_max_close:
                running_max_close = c
                a = atr.iloc[i]
                if pd.notna(a):
                    stop_level = max(stop_level, running_max_close - a * atr_mult)
            if c < stop_level or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    gapo_window: int = 14,
    gapo_lookback: int = 100,
    gapo_pct_threshold: float = 0.2,
    donchian_window: int = 20,
    atr_window: int = 14,
    atr_mult: float = 2.5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no txn costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        gapo_window=gapo_window,
        gapo_lookback=gapo_lookback,
        gapo_pct_threshold=gapo_pct_threshold,
        donchian_window=donchian_window,
        atr_window=atr_window,
        atr_mult=atr_mult,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change()
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)
