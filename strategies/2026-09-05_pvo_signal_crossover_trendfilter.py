"""Strategy: Percentage Volume Oscillator (PVO) signal-line crossover, gated
by a longer-term uptrend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-075):
The Percentage Volume Oscillator (PVO) is the PPO/MACD construction applied
to VOLUME instead of price: PVO = 100 * (EMA(fast_span, volume) -
EMA(slow_span, volume)) / EMA(slow_span, volume); Signal = EMA(signal_span,
PVO). Per mangrovedeveloper.ai's trading-signals reference (precise,
unambiguous rule definitions): "pvo_bullish_cross ... Check if PVO crosses
above signal line (bullish volume)" / "pvo_bearish_cross ... Check if PVO
crosses below signal line (bearish volume)". A PVO bullish cross signals
rising short-term volume momentum relative to its own longer-term volume
trend -- interpreted here as rising participation/conviction, gated by a
longer-term SMA price uptrend filter (this repo's standard convention for
oscillator-crossover strategies, since volume-momentum alone says nothing
about price direction) to only take the long entry when volume conviction
is rising AND price is already in an established uptrend. First
volume-oscillator-crossover (as opposed to raw-volume-threshold or OBV/CMF
family) strategy in this repo -- distinct from Klinger Volume Oscillator
(2026-09-04-084/085, EMA-difference of an H/L/C-trend-weighted volume-force
term, far more complex construction) and Volume-Weighted MACD
(2026-09-04-142, VWMA-difference of PRICE weighted by volume, not an
oscillator built purely on the volume series itself).

Signal logic
------------
- PVO(fast_span, slow_span) = 100 * (EMA(fast_span, volume) -
  EMA(slow_span, volume)) / EMA(slow_span, volume).
- Signal = EMA(signal_span, PVO).
- Entry (long): PVO crosses above Signal (bullish volume-momentum cross)
  AND close > SMA(trend_window) (uptrend gate).
- Exit: PVO crosses back below Signal (bearish volume-momentum cross), the
  trend filter breaks, or a max_hold_days time-stop.

Interface contract (RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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
    fast_span: int = 12,
    slow_span: int = 26,
    signal_span: int = 9,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    ema_fast = volume.ewm(span=fast_span, adjust=False).mean()
    ema_slow = volume.ewm(span=slow_span, adjust=False).mean()
    pvo = 100.0 * (ema_fast - ema_slow) / ema_slow.replace(0.0, pd.NA)
    signal = pvo.ewm(span=signal_span, adjust=False).mean()

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    bull_cross = (pvo > signal) & (pvo.shift(1) <= signal.shift(1))
    bear_cross = (pvo < signal) & (pvo.shift(1) >= signal.shift(1))

    entry = bull_cross.fillna(False) & uptrend.fillna(False)
    exit_trend_break = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(bear_cross.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
