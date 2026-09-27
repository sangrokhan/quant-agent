"""Strategy: Ehlers Roofing Filter, rolling z-scored, mean-reversion entry on
a CONFIRMED band re-entry (crossing back through the sigma threshold from the
extreme) plus a bar-color confirmation candle -- long-only daily-bar
adaptation.

Hypothesis (knowledge_base id 2026-09-27-1xx, this cron trigger):
Per algobot.live's "Roofing Filter Cycle Reversion" EA writeup (visited this
iteration, https://www.algobot.live/roofing-filter-cycle-reversion-ea-mt5/):
the Ehlers Roofing Filter (two-pole high-pass filter strips trend/DC drift,
then a Super Smoother low-pass strips noise, leaving a clean near-zero-mean
cycle wave) is normalized into a rolling z-score (NormWindow bars) so its
amplitude is comparable across calm and volatile regimes. The source's own
disclosed entry rule fades a CONFIRMED turn rather than a naked touch of the
extreme:
    Long entry: the z-scored roofing wave crosses back UP through
    -Threshold (leaving the oversold zone) AND the just-closed bar is
    bullish (close > open).
    Exit (source's short side is skipped here, long-only convention): the
    wave crosses back DOWN through +Threshold (leaving overbought) AND the
    just-closed bar is bearish (close < open); we additionally exit if the
    trend filter breaks or a max_hold_days time-stop is hit.

This is distinct from this repo's three prior Roofing Filter constructions
this cron trigger's earlier days (2026-09-22-056/058/059: self-lag Filt vs
1-bar-delayed Trigger crossover, and a raw-divergence continuous-sizing
dial) and from 2026-09-14-201 (rolling z-score + tanh continuous sizing on
the RAW roofing value, no band re-entry/bar-confirmation mechanic at all).
The novel elements here are (a) the explicit sigma BAND re-entry condition
(only counts a confirmed exit-from-extreme, not every zero-cross) and (b)
the bar-color confirmation candle, both taken directly from the source's
disclosed EA logic. Applied long-only on QQQ/SPY (equity) and BTC/USDT,
ETH/USDT (crypto) daily bars, gated by an SMA(trend_window) uptrend filter
(this repo's standard convention).

Roofing filter construction identical to this repo's existing Ehlers
Roofing Filter strategies (standard published two-pole HP + Super Smoother
LP coefficients, see strategies/2026-09-22_ehlers_roofing_filter_crossover.py
for the reference derivation).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} long/flat)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def _roofing_filter(close: pd.Series, hp_period: int, lp_period: int) -> pd.Series:
    """Ehlers two-pole high-pass filter followed by a Super Smoother low-pass."""
    n = len(close)
    price = close.to_numpy(dtype=float)

    alpha1 = (
        math.cos(0.707 * 2 * math.pi / hp_period)
        + math.sin(0.707 * 2 * math.pi / hp_period)
        - 1
    ) / math.cos(0.707 * 2 * math.pi / hp_period)

    hp = np.zeros(n)
    for t in range(n):
        if t < 2 or np.isnan(price[t]) or np.isnan(price[t - 1]) or np.isnan(price[t - 2]):
            hp[t] = 0.0
            continue
        hp[t] = (
            (1 - alpha1 / 2) ** 2 * (price[t] - 2 * price[t - 1] + price[t - 2])
            + 2 * (1 - alpha1) * hp[t - 1]
            - (1 - alpha1) ** 2 * hp[t - 2]
        )

    a1 = math.exp(-1.414 * math.pi / lp_period)
    b1 = 2 * a1 * math.cos(1.414 * math.pi / lp_period)
    c2 = b1
    c3 = -(a1 ** 2)
    c1 = 1 - c2 - c3

    filt = np.zeros(n)
    for t in range(n):
        if t < 2:
            filt[t] = 0.0
            continue
        filt[t] = c1 * (hp[t] + hp[t - 1]) / 2 + c2 * filt[t - 1] + c3 * filt[t - 2]

    return pd.Series(filt, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    hp_period: int = 48,
    lp_period: int = 10,
    norm_window: int = 50,
    threshold: float = 1.0,
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"] if "open" in df.columns else close.shift(1)

    filt = _roofing_filter(close, hp_period=hp_period, lp_period=lp_period)
    roll_mean = filt.rolling(norm_window).mean()
    roll_std = filt.rolling(norm_window).std()
    z = (filt - roll_mean) / roll_std.replace(0, float("nan"))

    bullish_bar = close > open_
    bearish_bar = close < open_

    # Confirmed re-entry through the band from the extreme side.
    cross_up_from_oversold = (z > -threshold) & (z.shift(1) <= -threshold)
    cross_down_from_overbought = (z < threshold) & (z.shift(1) >= threshold)

    entry_signal = cross_up_from_oversold & bullish_bar
    reverse_exit_signal = cross_down_from_overbought & bearish_bar

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    hold_count = 0
    warmup = max(hp_period, lp_period, norm_window, trend_window) + 5

    entry_arr = entry_signal.to_numpy()
    reverse_arr = reverse_exit_signal.to_numpy()
    uptrend_arr = uptrend.to_numpy()

    for i in range(len(close)):
        if i < warmup or not np.isfinite(z.iloc[i]):
            position.iloc[i] = 0
            continue
        if in_pos:
            hold_count += 1
            exit_signal = bool(reverse_arr[i]) or (not bool(uptrend_arr[i])) or (
                hold_count >= max_hold_days
            )
            if exit_signal:
                in_pos = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_arr[i]) and bool(uptrend_arr[i]):
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    hp_period: int = 48,
    lp_period: int = 10,
    norm_window: int = 50,
    threshold: float = 1.0,
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    positions = generate_signals(
        price_df,
        hp_period=hp_period,
        lp_period=lp_period,
        norm_window=norm_window,
        threshold=threshold,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    daily_returns = close.pct_change().fillna(0.0)
    strategy_returns = positions.shift(1).fillna(0).astype(float) * daily_returns
    return strategy_returns
