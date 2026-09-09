"""Strategy: Traders Dynamic Index (TDI) long-only crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-101):
Per Google AI-overview synthesis (TrendSpider/XBTFX/FX Replay sources,
query "Trader's Dynamic Index TDI indicator trading strategy exact entry
exit rules"): TDI combines RSI, Bollinger Bands, and moving averages into
one oscillator with four components -- Green Line (RSI itself, price
momentum), Red Line (Trade Signal Line, a smoothed MA of the Green
Line), Yellow Line (Market Base Line/MBL, a longer-term MA of RSI
showing trend bias), and Blue Lines (Bollinger Bands computed on RSI,
volatility bands). Source's exact long rule: trend filter (Yellow Line
flat-to-rising or above 50) + oversold condition (Green Line below 32 OR
outside the lower blue band) + crossover trigger (Green Line crosses
above Red Line) => long entry at the close of the crossover bar. Exit:
Green Line crosses back below Red Line (primary), OR reaching the 50
midline while riding a bigger trend wave (source's "trend momentum
exit," approximated here as an additional valid exit condition), OR
stop-loss below the recent swing low (approximated via a rolling-window
low).

First TDI (RSI + Bollinger-on-RSI + dual-MA-of-RSI) strategy in this
repo (0 prior hits on "TDI"/"Traders Dynamic Index") -- distinct from
plain RSI signal-line crossovers (e.g. Connors RSI, RSI(2)) since TDI
adds a volatility-band-on-RSI oversold trigger AND a separate longer-MA
trend-bias filter, both absent from this repo's existing RSI-family
strategies.

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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss.replace(0.0, float("nan"))
    rsi = 100 - 100 / (1 + rs)
    rsi = rsi.where(avg_loss != 0, 100.0)
    rsi = rsi.where(~((avg_loss == 0) & (avg_gain == 0)), 50.0)
    return rsi.astype(float)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 13,
    signal_window: int = 2,
    base_window: int = 34,
    bb_window: int = 34,
    bb_std: float = 1.618,
    oversold_level: float = 32.0,
    swing_lookback: int = 10,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]

    green = _rsi(close, rsi_window)
    red = green.rolling(signal_window).mean()
    yellow = green.rolling(base_window).mean()
    bb_mid = green.rolling(bb_window).mean()
    bb_std_val = green.rolling(bb_window).std()
    lower_band = bb_mid - bb_std * bb_std_val

    trend_ok = (yellow > yellow.shift(1)) | (yellow > 50)
    oversold = (green < oversold_level) | (green < lower_band)
    green_above_red = green > red
    crossover = green_above_red & (~green_above_red.shift(1).fillna(False))

    entry = trend_ok.fillna(False) & oversold.fillna(False) & crossover
    exit_cross = ~green_above_red
    exit_midline = (green >= 50) & (green.shift(1) < 50)

    swing_low = low.rolling(swing_lookback).min()

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = None

    for i in range(n):
        if in_position:
            held = i - entry_idx
            stop_hit = stop_price is not None and close.iloc[i] < stop_price
            if bool(exit_cross.iloc[i]) or bool(exit_midline.iloc[i]) or stop_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                stop_price = None
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                stop_price = swing_low.iloc[i]
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
