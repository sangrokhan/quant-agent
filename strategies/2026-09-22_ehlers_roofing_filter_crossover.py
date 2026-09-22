"""Strategy: Ehlers Roofing Filter fast/slow (1-bar-delayed) line crossover,
gated by an SMA trend filter.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per John F. Ehlers' "Cycle Analytics for Traders" (2013, ch.7), the Roofing
Filter combines a two-pole high-pass filter (removes long-period trend/DC
components below a low-cutoff period) with a Super Smoother low-pass filter
(removes noise above a high-cutoff period), isolating only the cyclic
components of price between the two critical periods. Per the TradingView
"[blackcat] L2 Ehlers Roofing Filter Indicator" description (read via
browser_exec this iteration -- web_search DDGS backend intermittently
TLS-erroring on several queries this session, Google SERP fallback used):
"The ideal time to buy is when the cycle is at a trough, and the ideal time
to exit a long position or to sell short is when the cycle is at a peak.
These conditions are flagged by the filter crossing itself delayed by one
bar" -- i.e. Filt (the roofing-filtered fast line) crossing above its own
1-bar-lagged value (Trigger) signals a cycle trough (long entry); crossing
below signals a cycle peak (exit). This repo has zero prior "Roofing Filter"
matches -- distinct from the already-saturated plain Super Smoother,
Fisher Transform, and other Ehlers-family entries (none combine the
two-pole HP + SuperSmoother LP "roofing" construction with a self-lag
crossover trigger). Applied long-only, gated by an SMA(trend_window) uptrend
filter (this repo's standard convention to avoid trading pure noise-cycle
signals against the prevailing trend), on QQQ/SPY (equity) and BTC/USDT,
ETH/USDT (crypto) daily bars.

Roofing filter construction (standard published Ehlers coefficients,
independent of API window inputs -- hp_period governs the two-pole
high-pass cutoff, lp_period governs the Super Smoother low-pass cutoff):

    alpha1 = (cos(0.707*2*pi/hp_period) + sin(0.707*2*pi/hp_period) - 1)
             / cos(0.707*2*pi/hp_period)
    HP[t] = (1-alpha1/2)^2 * (price[t] - 2*price[t-1] + price[t-2])
            + 2*(1-alpha1)*HP[t-1] - (1-alpha1)^2*HP[t-2]

    a1 = exp(-1.414*pi/lp_period)
    b1 = 2*a1*cos(1.414*pi/lp_period)
    c2 = b1; c3 = -a1^2; c1 = 1 - c2 - c3
    Filt[t] = c1*(HP[t]+HP[t-1])/2 + c2*Filt[t-1] + c3*Filt[t-2]

Trigger[t] = Filt[t-1] (the "filter crossing itself delayed by one bar").
Long entry: Filt crosses above Trigger (cycle trough) AND close > SMA(trend_window).
Exit: Filt crosses below Trigger (cycle peak), trend filter flips, or a
max_hold_days time-stop (this repo's standard convention to bound holding
periods for oscillator/cycle-based entries).

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
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    filt = _roofing_filter(close, hp_period=hp_period, lp_period=lp_period)
    trigger = filt.shift(1)

    cross_up = (filt > trigger) & (filt.shift(1) <= trigger.shift(1))
    cross_down = (filt < trigger) & (filt.shift(1) >= trigger.shift(1))

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    hold_count = 0
    warmup = max(hp_period, lp_period, trend_window) + 5

    for i in range(len(close)):
        if i < warmup:
            position.iloc[i] = 0
            continue
        if in_pos:
            hold_count += 1
            exit_signal = bool(cross_down.iloc[i]) or (not bool(uptrend.iloc[i])) or (
                hold_count >= max_hold_days
            )
            if exit_signal:
                in_pos = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entry_signal = bool(cross_up.iloc[i]) and bool(uptrend.iloc[i])
            if entry_signal:
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
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    daily_returns = close.pct_change().fillna(0.0)
    strategy_returns = positions.shift(1).fillna(0).astype(float) * daily_returns
    return strategy_returns
