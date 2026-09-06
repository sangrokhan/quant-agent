"""Strategy: Gaussian Channel trend-breakout, with an optional 200-SMA regime gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-XXX):
The Gaussian Channel (an IIR/bell-curve-weighted low-lag smoothing filter,
per DonovanWall's open-source "Gaussian Channel (DW)" indicator, widely
reused in TradingView community strategies -- source:
https://kr.tradingview.com/scripts/gaussianchannel , "TRADLEWARE - Gaussian
Channel + Stochastic RSI" strategy write-up) produces a smoothed midline
plus volatility-scaled upper/lower bands (offset by a multiple of a
filtered true-range measure). The midline's slope colors the channel
green (rising) or red (falling). The community strategy enters long when
the channel is green AND price closes above the upper band (a
trend-confirmed breakout), and exits when price closes back below the
upper band OR the channel flips from green to red. This repo simplifies
away the Stochastic RSI and bullish-candle micro-filters (kept out of
scope for a first test) but keeps the core channel-color + band-breakout
entry/exit logic and the optional 200-day SMA bull-regime gate, plus adds
a max_hold_days time-stop backstop (source doesn't specify one beyond its
"exit on band-reentry or color flip" rule).

Because this repo doesn't have a true recursive N-pole Gaussian IIR filter
available, the "poles" parameter is approximated by applying `poles`
successive passes of an EMA with span=sampling_period (a standard
practical approximation of a multi-pole low-pass filter chain -- each
additional pass increases smoothness/lag exactly as the source describes
poles behaving). This is a documented approximation, not the exact
DonovanWall recursive formula.

Signal logic
------------
- filter = `poles`-pass repeated-EMA(sampling_period) smoothing of close
  (approximates the Gaussian/IIR filter's smoothness-vs-lag behavior).
- channel_green = filter is higher than its value `slope_lookback` bars ago
  (rising midline = uptrend confirmed, "green"); red otherwise.
- true_range filtered the same way (repeated-EMA(sampling_period) of the
  classic True Range) scaled by tr_mult gives the band half-width:
  upper_band = filter + tr_mult * filtered_tr, lower_band = filter - tr_mult * filtered_tr.
- Entry (long): channel_green AND close crosses/is above upper_band, AND
  (if enabled) close > SMA(trend_window) bull-regime gate.
- Exit: close closes back below upper_band, OR channel flips green->red,
  OR a max_hold_days time-stop is hit.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _repeated_ema(series: pd.Series, span: int, poles: int) -> pd.Series:
    out = series.astype(float)
    for _ in range(max(1, poles)):
        out = out.ewm(span=span, adjust=False, min_periods=span).mean()
    return out


def _true_range(df: pd.DataFrame) -> pd.Series:
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
    return tr


def _compute_channel(
    price_df: pd.DataFrame,
    sampling_period: int,
    poles: int,
    tr_mult: float,
    slope_lookback: int,
):
    df = _prep(price_df)
    close = df["close"]

    filt = _repeated_ema(close, sampling_period, poles)
    tr = _true_range(df)
    filt_tr = _repeated_ema(tr, sampling_period, poles)

    upper_band = filt + tr_mult * filt_tr
    lower_band = filt - tr_mult * filt_tr
    channel_green = filt > filt.shift(slope_lookback)

    return df, close, filt, upper_band, lower_band, channel_green


def generate_signals(
    price_df: pd.DataFrame,
    sampling_period: int = 144,
    poles: int = 4,
    tr_mult: float = 1.414,
    slope_lookback: int = 5,
    trend_window: int | None = 200,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df, close, filt, upper_band, lower_band, channel_green = _compute_channel(
        price_df, sampling_period, poles, tr_mult, slope_lookback
    )

    breakout = close > upper_band
    regime_ok = pd.Series(True, index=close.index)
    if trend_window:
        sma = close.rolling(trend_window, min_periods=trend_window).mean()
        regime_ok = close > sma

    entry = channel_green & breakout & regime_ok
    exit_signal = (close < upper_band) | (~channel_green)

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    hold_days = 0
    for i in range(len(close)):
        if not in_pos:
            if bool(entry.iloc[i]):
                in_pos = True
                hold_days = 0
        else:
            hold_days += 1
            if bool(exit_signal.iloc[i]) or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
                position.iloc[i] = 0
                continue
        position.iloc[i] = 1 if in_pos else 0

    return position.fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    sampling_period: int = 144,
    poles: int = 4,
    tr_mult: float = 1.414,
    slope_lookback: int = 5,
    trend_window: int | None = 200,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return daily strategy returns (position lagged 1 day to avoid look-ahead)."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        sampling_period=sampling_period,
        poles=poles,
        tr_mult=tr_mult,
        slope_lookback=slope_lookback,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    lagged_position = position.shift(1).fillna(0)
    strat_returns = lagged_position * daily_ret
    return strat_returns.fillna(0.0)
