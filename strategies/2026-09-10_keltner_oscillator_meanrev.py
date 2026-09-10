"""Strategy: Keltner Channel Oscillator (normalized %B-style) mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per https://tradesmart.com/blog/technical-analysis-keltner-channel-oscillator/
(visited this iteration), the Keltner Channel Oscillator normalizes price's
position within its own Keltner Channel into a bounded value:

    KC middle = EMA(close, ema_window)          [source default 20]
    KC upper  = middle + atr_mult * ATR(atr_window)   [source default mult=2]
    KC lower  = middle - atr_mult * ATR(atr_window)
    Oscillator = (Price - KC_lower) / (KC_upper - KC_lower) - 0.5

roughly bounded [-0.5, +0.5]: values above zero mean price sits closer to
the upper band (overbought), below zero means closer to the lower band
(oversold). This is analogous to Bollinger %B but built on ATR-based
Keltner bands instead of std-dev bands. First Keltner Channel OSCILLATOR
(normalized %B-style value) strategy in this repo -- distinct from this
repo's already-tested Keltner breakout (raw upper-band cross, 2026-09-03-016)
and Keltner mean-reversion band-touch (raw lower-band touch, 2026-09-05-074)
strategies, which both trade the raw band touch/cross rather than this
continuous normalized oscillator value.

Signal logic
------------
- Entry (long): Oscillator crosses from <= oversold_level (a negative
  threshold, e.g. -0.5 = exactly at the lower band) back up above it --
  i.e. price bouncing off an oversold extreme -- gated by close above a
  longer-term SMA trend filter (this repo's own repeated finding that mean
  reversion entries need a broader-trend gate to avoid buying into genuine
  downtrends).
- Exit: Oscillator crosses back above the exit_level (source's own
  zero-line "middle of the channel" interpretation, i.e. reversion
  complete), or a max_hold_days time-stop.
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


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prior_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prior_close).abs(),
            (low - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _keltner_oscillator(
    df: pd.DataFrame, ema_window: int, atr_window: int, atr_mult: float
) -> pd.Series:
    close = df["close"]
    middle = close.ewm(span=ema_window, adjust=False).mean()
    atr = _atr(df, atr_window)
    upper = middle + atr_mult * atr
    lower = middle - atr_mult * atr
    band_width = (upper - lower).replace(0.0, pd.NA)
    osc = (close - lower) / band_width - 0.5
    return osc


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 20,
    atr_window: int = 10,
    atr_mult: float = 2.0,
    oversold_level: float = -0.5,
    exit_level: float = 0.0,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    osc = _keltner_oscillator(df, ema_window, atr_window, atr_mult)
    sma = close.rolling(trend_window).mean()

    entry_signal = (osc > oversold_level) & (osc.shift(1) <= oversold_level) & (close > sma)
    exit_signal = osc > exit_level

    valid = osc.notna() & sma.notna()

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
    ema_window: int = 20,
    atr_window: int = 10,
    atr_mult: float = 2.0,
    oversold_level: float = -0.5,
    exit_level: float = 0.0,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        ema_window=ema_window,
        atr_window=atr_window,
        atr_mult=atr_mult,
        oversold_level=oversold_level,
        exit_level=exit_level,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(int) * daily_ret
    strat_returns.name = "strategy_returns"
    return strat_returns
