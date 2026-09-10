"""Strategy: Donchian midline pullback + CCI zero-cross dual confirmation
(the "Rogue Kestrel" trend-continuation setup).

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per https://tradingstrategyguides.com/the-rogue-kestrel-precision-donchian-cci-pullback-strategy/
(visited this iteration), a fully-disclosed trend-continuation pullback
system:

1. Trend filter: close above a rising 50-period EMA (long side only, per
   this repo's long-only convention).
2. Structural expansion: price printed a fresh 20-period Donchian HIGH
   within the last `lookback_bars` bars (confirms an active uptrend, not
   consolidation).
3. Pullback + momentum reset: price retraces to touch/cross the 20-period
   Donchian MIDLINE (basis = (upper+lower)/2) while CCI(20) dips below
   zero during the retracement (short-term selling pressure completing a
   cycle).
4. Dual confirmation trigger: entry when price closes back ABOVE the
   Donchian midline on the SAME bar that CCI(20) closes back above zero --
   source's own explicit "both conditions must print on the exact same
   candle close" rule.

Adapted from the source's intraday/swing execution (fixed R-multiple
targets, tick-based stops) to this repo's daily-bar/vectorbt framework: exit
on price closing back below the midline (source's own structural
invalidation logic) or a max_hold_days time-stop, rather than fixed
R-multiple profit targets. First Donchian-midline + CCI dual-same-candle-
confirmation strategy in this repo -- distinct from the already-tested
Donchian midline false-break fade (2026-09-08-017, mean-reversion TO the
midline, decisively rejected) since this is a trend-CONTINUATION pullback
bouncing FROM the midline back toward the trend, not a fade targeting it.

Signal logic
------------
- Entry (long): close > EMA(50) AND EMA(50) has a positive slope over
  ema_slope_window bars AND a fresh Donchian(donchian_window)-period high
  was set within the last lookback_bars bars AND CCI(cci_window) was
  negative within the last few bars (pullback reset) AND on this bar,
  close crosses above the Donchian midline while CCI crosses above zero
  (same-bar dual confirmation).
- Exit: close crosses back below the Donchian midline, or a max_hold_days
  time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _cci(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    typical_price = (high + low + close) / 3.0
    sma_tp = typical_price.rolling(period).mean()
    import numpy as np

    mean_dev = typical_price.rolling(period).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    )
    mean_dev = mean_dev.replace(0.0, pd.NA)
    return (typical_price - sma_tp) / (0.015 * mean_dev)


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 50,
    ema_slope_window: int = 5,
    donchian_window: int = 20,
    lookback_bars: int = 15,
    cci_window: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high, low = df["high"], df["low"]

    ema = close.ewm(span=ema_window, adjust=False).mean()
    ema_slope_up = ema > ema.shift(ema_slope_window)

    donchian_high = high.rolling(donchian_window).max()
    donchian_low = low.rolling(donchian_window).min()
    donchian_mid = (donchian_high + donchian_low) / 2.0

    fresh_high = high >= donchian_high  # today set (or tied) the rolling high
    expansion_recent = fresh_high.rolling(lookback_bars).max().astype(bool)

    cci = _cci(df, cci_window)
    cci_was_negative_recent = (cci < 0).rolling(3).max().astype(bool)

    cross_above_mid = (close > donchian_mid) & (close.shift(1) <= donchian_mid.shift(1))
    cci_cross_above_zero = (cci > 0) & (cci.shift(1) <= 0)

    entry_signal = (
        (close > ema)
        & ema_slope_up
        & expansion_recent
        & cci_was_negative_recent.shift(1).fillna(False)
        & cross_above_mid
        & cci_cross_above_zero
    )

    exit_signal = close < donchian_mid

    valid = donchian_mid.notna() & ema.notna() & cci.notna()

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = None

    for i in range(len(df.index)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue

        if in_position:
            held_days = i - entry_idx
            if exit_signal.iloc[i] or held_days >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_signal.iloc[i]:
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    ema_window: int = 50,
    ema_slope_window: int = 5,
    donchian_window: int = 20,
    lookback_bars: int = 15,
    cci_window: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        ema_window=ema_window,
        ema_slope_window=ema_slope_window,
        donchian_window=donchian_window,
        lookback_bars=lookback_bars,
        cci_window=cci_window,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(int) * daily_ret
    strat_returns.name = "strategy_returns"
    return strat_returns
