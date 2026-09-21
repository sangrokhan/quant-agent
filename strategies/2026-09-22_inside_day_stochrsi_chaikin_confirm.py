"""Strategy: Inside-Day pattern confirmed by StochRSI oversold + Chaikin
Oscillator zero-line sign (long-only), exit on Chaikin Osc crossing back
below zero or a max-hold time-stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-014):
Per TradingSim's "Inside Day + Chaikin + Stochastic RSI" article
(https://www.tradingsim.com/blog/inside-day, visited this iteration), an
Inside Day (ID) candle -- today's high < yesterday's high AND today's low >
yesterday's low -- is a low-information pattern on its own (a pause/breather
bar) and needs oscillator confirmation to pick a direction. The article's
own worked example enters long when: (1) Stochastic RSI is/was in the
oversold zone (identifying a washed-out entry point), (2) the Chaikin
Oscillator is on the bullish (positive) side of its zero line (proxy for
the article's subjective "bullish divergence" call), and (3) an Inside Day
prints. Exit is triggered when the Chaikin Oscillator crosses below zero
(momentum flips bearish).

This repo already has separate Inside Day strategies (2026-09-07-006/007/008,
gap-down-pullback + trend-SMA gated variants, no oscillator confirmation)
and separate Chaikin Oscillator strategies, but none combine Inside Day +
StochRSI + Chaikin Oscillator zero-line together -- that specific 3-signal
confluence is the new, testable angle from this source.

Signal logic
------------
- Inside Day (ID): high < prior high AND low > prior low.
- StochRSI(rsi_window, stoch_window) < oversold_threshold at some point in
  the lookback_days window ending on/before the ID bar (the "was in
  oversold" confirmation, since the ID bar itself may not be the exact
  oversold bar).
- Chaikin Oscillator (fast_ema - slow_ema of the Accumulation/Distribution
  line) > 0 on the ID bar (bullish side of zero).
- Entry (long): all three conditions true on the same bar -> enter at
  next bar's open (implemented here as same-bar signal, executed with the
  standard next-day-return shift used throughout this repo).
- Exit: Chaikin Oscillator crosses from >=0 to <0 (bearish flip), OR
  max_hold_days elapsed, whichever comes first.
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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def _stoch_rsi(close: pd.Series, rsi_window: int, stoch_window: int) -> pd.Series:
    rsi = _rsi(close, rsi_window)
    lo = rsi.rolling(stoch_window).min()
    hi = rsi.rolling(stoch_window).max()
    return ((rsi - lo) / (hi - lo).replace(0.0, 1e-12)) * 100.0


def _chaikin_osc(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series,
    fast: int, slow: int,
) -> pd.Series:
    hl_range = (high - low).replace(0.0, 1e-12)
    mfm = ((close - low) - (high - close)) / hl_range
    mfv = mfm * volume
    adl = mfv.cumsum()
    fast_ema = adl.ewm(span=fast, adjust=False).mean()
    slow_ema = adl.ewm(span=slow, adjust=False).mean()
    return fast_ema - slow_ema


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    stoch_window: int = 14,
    oversold_threshold: float = 20.0,
    lookback_days: int = 5,
    chaikin_fast: int = 3,
    chaikin_slow: int = 10,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]

    inside_day = (high < high.shift(1)) & (low > low.shift(1))

    stoch_rsi = _stoch_rsi(close, rsi_window, stoch_window)
    was_oversold = (
        stoch_rsi.rolling(lookback_days, min_periods=1)
        .min()
        .le(oversold_threshold)
    )

    chaikin = _chaikin_osc(high, low, close, volume, chaikin_fast, chaikin_slow)
    chaikin_bullish = chaikin > 0.0
    chaikin_bear_flip = (chaikin < 0.0) & (chaikin.shift(1) >= 0.0)

    entry = inside_day & was_oversold.fillna(False) & chaikin_bullish.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(chaikin_bear_flip.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
