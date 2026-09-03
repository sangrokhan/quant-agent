"""Strategy: Mass Index reversal bulge, EMA-slope filtered, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-075):
Donald Dorsey's Mass Index measures the widening then narrowing of the
daily high-low range (a non-directional volatility-expansion/contraction
gauge), computed as the 25-period sum of the ratio of a 9-period EMA of the
high-low range to its own double-smoothed 9-period EMA. The "reversal
bulge" signal fires when the index climbs above 27 then drops back below
26.5 -- signaling the range has widened sharply then started to contract,
often preceding a trend reversal. Since the indicator itself gives no
directional clue, it must be paired with a trend filter: per multiple
corroborating sources (onetradejournal.com, GoCharting, TradingSim,
PineScriptForge, Google AI-overview synthesis), a bullish long entry
requires (1) a completed reversal bulge, (2) the prior trend/9-EMA slope
was heading DOWNWARD (contrarian precondition -- the bulge marks the
END of that downtrend), and (3) trigger: price closes above the 9-EMA.
Exit when price closes back below the 9-EMA. First Mass Index (range-ratio
volatility-widening gauge, distinct from ATR/Choppiness Index which measure
absolute range magnitude rather than the RATIO of single- to double-smoothed
range) strategy tested in this repo.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _mass_index(df: pd.DataFrame, ema_span: int = 9, sum_window: int = 25) -> pd.Series:
    hl_range = df["high"] - df["low"]
    single_ema = hl_range.ewm(span=ema_span, adjust=False).mean()
    double_ema = single_ema.ewm(span=ema_span, adjust=False).mean()
    ratio = single_ema / double_ema
    mass_index = ratio.rolling(sum_window).sum()
    return mass_index


def generate_signals(
    price_df: pd.DataFrame,
    ema_span: int = 9,
    sum_window: int = 25,
    bulge_high: float = 27.0,
    bulge_low: float = 26.5,
    trend_ema_span: int = 9,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: a completed reversal bulge (Mass Index crossed above bulge_high
    at some point since the last time it was below bulge_low, then drops
    back below bulge_low) AND the trend_ema slope was downward just before
    the bulge completed AND price closes above the trend EMA (trigger).
    Exit: price closes back below the trend EMA.
    """
    df = _prep(price_df)
    close = df["close"]
    mass_index = _mass_index(df, ema_span=ema_span, sum_window=sum_window)
    trend_ema = close.ewm(span=trend_ema_span, adjust=False).mean()
    ema_slope_down = trend_ema.diff() < 0

    above_high = mass_index > bulge_high
    # "Armed" once MI crosses above bulge_high; bulge completes when it
    # subsequently drops below bulge_low while still armed.
    armed = False
    bulge_completed = pd.Series(False, index=df.index)
    for i in range(len(df)):
        mi = mass_index.iloc[i]
        if pd.isna(mi):
            continue
        if mi > bulge_high:
            armed = True
        elif armed and mi < bulge_low:
            bulge_completed.iloc[i] = True
            armed = False

    entry_trigger = bulge_completed & ema_slope_down.shift(1).fillna(False) & (close > trend_ema)
    exit_signal = close < trend_ema

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    # Track whether a bulge has "recently completed" (allow the price
    # trigger to fire within a short window after the bulge, not only the
    # exact same bar) -- use a small lookback of 5 bars.
    recent_bulge = bulge_completed.rolling(5, min_periods=1).max().astype(bool)
    entry_trigger = recent_bulge & ema_slope_down.shift(1).fillna(False) & (close > trend_ema) & (close.shift(1) <= trend_ema.shift(1))

    for i in range(len(df)):
        if in_position:
            if bool(exit_signal.iloc[i]) if not pd.isna(exit_signal.iloc[i]) else False:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]) if not pd.isna(entry_trigger.iloc[i]) else False:
                in_position = True
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
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
