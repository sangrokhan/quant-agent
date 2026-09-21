"""Strategy: XLP-style range-band + IBS mean reversion (rolling-high-anchored
band, inverse-IBS confirmation filter).

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per quantifiedstrategies.com's "10 Best Swing Trading Strategies 2026"
article, strategy #7 "XLP mean reversion strategy" (fully disclosed rule
text, read via browser_exec -- web_search intermittently TLS-erroring this
iteration, resolved via Google SERP fallback):
    1. avg_range = rolling mean of (High-Low) over band_window (25) days.
    2. IBS = (Close-Low)/(High-Low), the standard Internal Bar Strength.
    3. lower_band = rolling_high(band_window) - band_mult(2.0)*avg_range.
    4. Entry: close < lower_band AND IBS > ibs_threshold(0.4) -> go long
       at the close.
    5. Exit: close > previous day's high.

This repo already has two similar rolling-high-anchored-band + IBS
strategies (2026-09-08-133 rejected: 10-day high, 2.5x mult, IBS<0.3,
SMA(300) gate; 2026-09-09-041 accepted: same band, dynamic SMA stop exit).
This variant is distinct on three counts the source itself specifies: (1)
a 25-day (not 10-day) rolling high for the band anchor, (2) a 2.0x (not
2.5x) average-range multiplier, (3) an IBS filter requiring IBS > 0.4 (the
OPPOSITE direction from every other IBS entry in this repo, which all
require LOW IBS as an oversold-close signal) -- the source's own rationale
being that the close should NOT be sitting at the day's dead low (avoid
catching a still-falling knife), just below a stretched band with some
intraday recovery already underway. No trend filter, no dynamic stop --
exit purely on close > prior day's high (source's disclosed exact rule).

Signal logic
------------
- avg_range = rolling mean of (High-Low), band_window periods.
- rolling_high = rolling max of High, band_window periods.
- lower_band = rolling_high - band_mult * avg_range.
- IBS = (Close-Low)/(High-Low).
- Entry (long) at close when: close < lower_band AND IBS > ibs_threshold.
- Exit at close when: close > previous day's high.
- Flat otherwise. max_hold_days safety valve added (source has no explicit
  time-stop; this repo's convention bounds worst-case holding period).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    band_window: int = 25,
    band_mult: float = 2.0,
    ibs_threshold: float = 0.4,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    avg_range = (high - low).rolling(band_window).mean()
    rolling_high = high.rolling(band_window).max()
    lower_band = rolling_high - band_mult * avg_range

    hl_range = (high - low).replace(0, pd.NA)
    ibs = (close - low) / hl_range

    entry = (close < lower_band) & (ibs > ibs_threshold)
    prev_high = high.shift(1)
    exit_signal = close > prev_high

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) if pd.notna(entry.iloc[i]) else False:
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strategy_ret
