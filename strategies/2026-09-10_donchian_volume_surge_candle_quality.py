"""Strategy: Donchian channel breakout, gated by a volume-surge filter AND a
candle-quality (body-to-range) filter, exiting via an ATR-buffered channel
midline stop rather than a fixed trailing-low.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-123):
Per a Google AI-overview synthesis (LuxAlgo/JournalPlus/TrendSpider/
avatrade.co.za sourced) of "Donchian channel breakout with volume surge
confirmation": a close breaking cleanly above the N-day upper Donchian band
is a stronger, less-fakeout-prone long entry when (1) the breakout bar's
volume is >= a multiplier x its own N-day average volume (source: "1.5x to
2x the 20-bar average volume... proving institutional participation"), AND
(2) the breakout candle's body comprises a large fraction (source: "60% or
more") of its own high-low range (filters weak doji/pin-bar closes at the
edge of the range). Exit management per the source's own stated rule: stop
near the channel MIDLINE, buffered by an ATR multiple below/above the
opposite structure, rather than a fixed trailing-low exit.

This is distinct from prior Donchian-family entries in this repo:
- 2026-09-04-166 (RVOL spike >= 1.5x gate) used a shorter-term trailing-low
  exit, NOT a candle-body-quality filter and NOT an ATR-buffered midline
  stop.
- 2026-09-05-060 (Donchian + OBV breakout) used a volume-derived indicator
  (OBV) breaking its own rolling high, not a raw volume-multiple threshold,
  and had no candle-quality filter.
- 2026-09-03-008 / 2026-09-04-054 (Turtle-style Donchian breakouts) had no
  volume filter at all.
This combination (volume-surge multiple + candle-body-quality filter +
ATR-buffered midline exit, together) has not been tested in this repo.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
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
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    donchian_window: int = 20,
    vol_avg_window: int = 20,
    vol_surge_mult: float = 1.5,
    min_body_ratio: float = 0.60,
    atr_window: int = 14,
    atr_stop_mult: float = 1.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, open_, high, low, volume = (
        df["close"],
        df["open"],
        df["high"],
        df["low"],
        df["volume"],
    )

    upper_band = high.rolling(donchian_window).max().shift(1)
    donchian_mid = (
        high.rolling(donchian_window).max() + low.rolling(donchian_window).min()
    ) / 2.0
    donchian_mid = donchian_mid.shift(1)

    avg_volume = volume.rolling(vol_avg_window).mean()
    volume_surge = volume >= (avg_volume * vol_surge_mult)

    candle_range = (high - low).replace(0.0, pd.NA)
    body_ratio = (close - open_).abs() / candle_range
    body_ratio = body_ratio.fillna(0.0)
    candle_quality = body_ratio >= min_body_ratio

    atr = _atr(df, atr_window)

    breakout_entry = (
        (close > upper_band) & volume_surge & candle_quality & upper_band.notna()
    )

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = None

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            mid = donchian_mid.iloc[i]
            a = atr.iloc[i]
            if pd.notna(mid) and pd.notna(a):
                stop_level = mid - atr_stop_mult * a
            exit_stop = stop_level is not None and close.iloc[i] < stop_level
            if exit_stop or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                stop_level = None
                continue
            position.iloc[i] = 1
        else:
            if bool(breakout_entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
                mid = donchian_mid.iloc[i]
                a = atr.iloc[i]
                stop_level = (mid - atr_stop_mult * a) if pd.notna(mid) and pd.notna(a) else None
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
