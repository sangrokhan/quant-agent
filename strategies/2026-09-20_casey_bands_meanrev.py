"""Strategy: Casey Bands Mean Reversion (Close% / PercentC threshold entry).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-133):
Per Ali Casey's "Casey Bands" (StatOasis, "Keltner Channels vs Bollinger
Bands: 116,640 Backtests (and the Third Band I Built)",
https://statoasis.com/overfit/research/how-to-build-a-profitable-strategy-using-casey-bands-(free-code-included),
visited via browser_exec this iteration): unlike Bollinger Bands (centered
on a simple average of the CLOSE, half-width = std-dev multiplier) or
Keltner Channels (centered on an EMA of the close, half-width =
ATR multiplier), Casey Bands anchor the upper band to a smoothed EMA of
the HIGHS and the lower band to a smoothed EMA of the LOWS -- so the
channel reflects where price actually REACHED, not where it settled. Half
-width is an ATR multiplier (published default: 20-period band length,
1.25x ATR multiplier, 3-bar smoothing). "Close%"/PercentC (analogous to
Bollinger's %B) measures where today's close sits between the two bands,
scaled 0-100. The source's own large-scale sweep found Casey Bands' most
durable SPY mean-reversion setting beat buy-and-hold on MAR even after
0.05% round-trip transaction costs, comparably to Bollinger/Keltner. First
Casey Bands strategy in this repo -- distinct from all prior Bollinger %B
and Keltner-Channel constructions (different band anchor: high/low extremes
vs close-based average).

Signal logic
------------
- upper_band = EMA(high, band_length, smoothing) + atr_mult * ATR(band_length)
- lower_band = EMA(low, band_length, smoothing) - atr_mult * ATR(band_length)
  (smoothing applied as an additional EMA pass over the raw high/low EMA,
  per source's "exponential average ... then smoothed" description)
- percent_c = (close - lower_band) / (upper_band - lower_band) * 100
- Entry (long): percent_c crosses below entry_level (mean-reversion into
  oversold territory relative to the high/low-anchored channel).
- Exit: percent_c crosses above exit_level, OR max_hold_days time-stop.
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    band_length: int = 20,
    atr_mult: float = 1.25,
    smoothing: int = 3,
    entry_level: float = 20.0,
    exit_level: float = 80.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    high_ema = high.ewm(span=band_length, adjust=False).mean().ewm(span=smoothing, adjust=False).mean()
    low_ema = low.ewm(span=band_length, adjust=False).mean().ewm(span=smoothing, adjust=False).mean()
    atr = _atr(df, band_length)

    upper_band = high_ema + atr_mult * atr
    lower_band = low_ema - atr_mult * atr

    band_width = (upper_band - lower_band).replace(0, float("nan"))
    percent_c = ((close - lower_band) / band_width * 100.0)

    entry_cross = (percent_c < entry_level) & (percent_c.shift(1) >= entry_level)
    exit_cross = (percent_c > exit_level) & (percent_c.shift(1) <= exit_level)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_cross.iloc[i]):
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
