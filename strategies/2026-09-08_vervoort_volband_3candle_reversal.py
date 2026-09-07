"""Strategy: Vervoort Volatility Band 3-candle long-only reversal system.

Hypothesis (knowledge_base id=2026-09-08-022):
Per marketcalls.in's "Volatility Band - Long Only Reversal Trading System"
(https://www.marketcalls.in/amibroker/volatility-band-long-only-reversal-trading-system.html,
mechanical rule confirmed via Google's summary of the same page), a 3-candle
sequence around the lower volatility band signals an oversold reversal:
(1) a candle closes below the lower band, (2) the next candle closes back
above the lower band (initial rejection of the extreme), (3) the candle
after that closes higher than candle 2 (confirms upward momentum shift) ->
long entry on candle 3's close. The source credits Sylvain Vervoort's
"highly smoothed" volatility-band style; since the exact Vervoort band
formula page (thinkorswim/TradingView Pine source) 404'd this iteration, we
approximate the band with a standard smoothed construction consistent with
that description: EMA(basis_window) of typical price (H+L+C)/3, offset by
atr_mult * ATR(atr_window) (a Keltner-style smoothed volatility band, not a
raw stdev band). This repo has tested two other Vervoort-attributed
indicators (2026-09-06-114 Inverse Fisher Transform of Stochastic,
2026-09-06-119 Zero-Lag Rainbow %B) but never this specific 3-candle
price-action confirmation pattern around a volatility band -- mechanically
distinct since it's a raw close-sequence pattern trigger, not an
oscillator threshold/crossover.

Signal logic
------------
- typical price = (high + low + close) / 3
- basis = EMA(basis_window) of typical price
- ATR(atr_window) (Wilder-style true range EMA)
- lower band = basis - atr_mult * ATR
- upper band = basis + atr_mult * ATR
- Pattern trigger (evaluated at each bar i, using bars i-2, i-1, i):
    bar[i-2].close < lower_band[i-2]   (first candle closes below lower band)
    bar[i-1].close > lower_band[i-1]   (second candle closes back above)
    bar[i].close   > bar[i-1].close    (third candle closes higher)
  -> long entry at close of bar i.
- Exit: close crosses back above the upper band (reversal target reached,
  own reasonable choice since the source doesn't specify an exit rule
  explicitly), OR held >= max_hold_days time-stop.

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
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    basis_window: int = 20,
    atr_window: int = 14,
    atr_mult: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    basis = typical.ewm(span=basis_window, adjust=False).mean()
    atr = _atr(df, atr_window)
    lower_band = basis - atr_mult * atr
    upper_band = basis + atr_mult * atr

    below_lower = close < lower_band
    back_above = close > lower_band

    n = len(close)
    entry = pd.Series(False, index=close.index)
    for i in range(2, n):
        if bool(below_lower.iloc[i - 2]) and bool(back_above.iloc[i - 1]) and close.iloc[i] > close.iloc[i - 1]:
            entry.iloc[i] = True

    exit_target = close > upper_band

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_target.iloc[i]) or held >= max_hold_days:
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
