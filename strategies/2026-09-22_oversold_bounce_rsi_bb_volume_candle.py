"""Strategy: Tradewink 'Oversold Bounce Setup' -- RSI + Bollinger + SMA200
trend filter + volume-spike confirmation + reversal-candle confirmation,
combined as an AND-gate long-only mean-reversion entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Per Tradewink's "Mean Reversion Trading: Strategy Guide with Entry Rules &
Examples" (https://www.tradewink.com/learn/mean-reversion-trading-strategy,
"The Oversold Bounce Setup (Long)" section, read via browser_exec this
iteration -- web_extract's ddgs backend cannot fetch page bodies), the
source's own disclosed 6-part entry checklist is:
    1. RSI(14) < 30 (oversold)
    2. Price at or below the lower Bollinger Band (20, 2 std)
    3. Stock is above its 200-day moving average (long-term uptrend intact)
    4. Volume spike: current volume > 1.5x its 20-day average volume
    5. Reversal candle: hammer, doji, or bullish engulfing on the entry bar
    6. No negative catalyst (not implementable from OHLCV alone -- skipped)
Exit per the source's disclosed exit menu: "Return to Mean" (price back to
the middle/basis band) is used here as the primary exit, backstopped by a
max_hold_days time-stop (source also lists trailing-stop/hard-stop variants
not implemented here to keep the test to the source's core disclosed rule).

Novelty vs prior repo entries: this repo has separately tested RSI+BB+volume
combos on crypto 4h bars without an SMA200 trend filter or candle
confirmation (2026-09-08-090, rejected, crypto only), and standalone
Hammer/Doji/Bullish-Engulfing candlestick patterns without an
RSI+BB+Volume co-gate (2026-09-06 Hammer, 2026-09-09 Bullish Doji Star,
Bullish Engulfing 2026-09-04-102). This is the first strategy in this repo
to combine ALL FIVE of RSI(14) oversold + Bollinger lower-band touch +
SMA(200) uptrend + volume-spike confirmation + a reversal-candle OR-gate
(hammer/doji/bullish-engulfing) into a single AND-gated entry, on daily
equity + crypto bars.

Signal logic
------------
- RSI(14, Wilder smoothing) < rsi_oversold.
- close <= lower Bollinger Band(bb_window, bb_std).
- close > SMA(trend_window) [200-day uptrend filter].
- volume > vol_mult * rolling SMA(volume, vol_window) [volume spike].
- Reversal-candle OR-gate on the same bar:
    * Hammer: lower_wick >= hammer_wick_ratio * body AND upper_wick <= body
      AND body <= 0.4 * full_range (small body near top of range).
    * Doji: body <= doji_body_frac * full_range (very small body).
    * Bullish engulfing: today bullish (close>open), yesterday bearish
      (close<open), today's body fully engulfs yesterday's body
      (open<=prev_close AND close>=prev_open).
- Entry: all five conditions true on the same bar -> long, acted on next
  bar's close per this repo's shift(1) execution-lag convention.
- Exit: close crosses back above the Bollinger middle band (SMA(bb_window),
  "return to mean"), OR a max_hold_days time-stop.

Interface contract (see validation/validators.py, validation/grid_test.py):
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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    rsi_oversold: float = 30.0,
    bb_window: int = 20,
    bb_std: float = 2.0,
    trend_window: int = 200,
    vol_window: int = 20,
    vol_mult: float = 1.5,
    hammer_wick_ratio: float = 2.0,
    doji_body_frac: float = 0.1,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    rsi = _rsi(close, rsi_window)

    sma_bb = close.rolling(bb_window).mean()
    std_bb = close.rolling(bb_window).std()
    lower_band = sma_bb - bb_std * std_bb

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    vol_avg = volume.rolling(vol_window).mean()
    vol_spike = volume > (vol_mult * vol_avg)

    body = (close - open_).abs()
    full_range = (high - low).replace(0.0, float("nan"))
    lower_wick = pd.concat([open_, close], axis=1).min(axis=1) - low
    upper_wick = high - pd.concat([open_, close], axis=1).max(axis=1)

    hammer = (
        (lower_wick >= hammer_wick_ratio * body)
        & (upper_wick <= body)
        & (body <= 0.4 * full_range)
    )
    doji = body <= (doji_body_frac * full_range)

    prev_open = open_.shift(1)
    prev_close = close.shift(1)
    bullish_engulf = (
        (close > open_)
        & (prev_close < prev_open)
        & (open_ <= prev_close)
        & (close >= prev_open)
    )

    reversal_candle = (hammer | doji | bullish_engulf).fillna(False)

    entry = (
        (rsi < rsi_oversold).fillna(False)
        & (close <= lower_band).fillna(False)
        & uptrend.fillna(False)
        & vol_spike.fillna(False)
        & reversal_candle
    )
    exit_meanrev = (close > sma_bb).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
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
