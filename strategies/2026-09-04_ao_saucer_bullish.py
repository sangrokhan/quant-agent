"""Strategy: Bill Williams' Awesome Oscillator (AO) Bullish Saucer setup.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-111):
The Awesome Oscillator's "Saucer" setup — a sharper, more localized momentum
re-acceleration signal than the plain zero-line cross previously tested
(id=2026-09-04-041, rejected as a near-miss: Sharpe 0.89 vs 1.0 threshold on
QQQ) — should perform better because it fires only when short-term momentum
is *already positive and confirmed* (AO above zero) and specifically catches
a brief pullback-then-reacceleration within that established uptrend, rather
than reacting to the noisier raw zero-line cross itself.

Per TradingView's official AO documentation (source of this hypothesis):
    AO = SMA(5, median_price) - SMA(34, median_price), median_price=(H+L)/2
    Bullish Saucer: AO is above the zero line; two consecutive red
    (declining) bars occur (2nd bar lower than 1st), followed by a green
    (rising) bar. That 3rd bar's close is the entry signal.

Signal logic
------------
- AO = SMA(ao_fast, median_price) - SMA(ao_slow, median_price).
- "Red" bar: AO(t) < AO(t-1). "Green" bar: AO(t) > AO(t-1).
- Bullish Saucer at bar t: AO(t) > 0 AND AO(t) > 0 (also true at t-1, t-2 by
  definition of "above zero line the entire time") AND AO(t-2) is red
  relative to AO(t-3) is NOT required by the source (only the two red bars
  need to be internally decreasing) -- so: AO(t-1) < AO(t-2) (1st red bar,
  bar t-2->t-1 declining) AND AO(t) is NOT used for the red-pair itself;
  concretely as implemented: bar (t-2) and bar (t-1) are both red with
  AO(t-1) < AO(t-2) (second red bar lower than first), AND bar t is green
  (AO(t) > AO(t-1)), AND AO(t) > 0 (all three bars above the zero line,
  consistent with the source's "AO is above the Zero Line" framing).
- Optional trend filter: close > SMA(trend_window) (long-term uptrend gate,
  same rationale as the previously-tested zero-line-cross variant).
- Exit: AO crosses back below zero (momentum regime flip), OR a Bearish
  Saucer fires (AO below zero mirror-image), OR after max_hold_days.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _awesome_oscillator(df: pd.DataFrame, ao_fast: int, ao_slow: int) -> pd.Series:
    median_price = (df["high"] + df["low"]) / 2.0
    return median_price.rolling(ao_fast).mean() - median_price.rolling(ao_slow).mean()


def generate_signals(
    price_df: pd.DataFrame,
    ao_fast: int = 5,
    ao_slow: int = 34,
    trend_window: int = 200,
    use_trend_filter: bool = True,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ao = _awesome_oscillator(df, ao_fast, ao_slow)
    ao_prev1 = ao.shift(1)
    ao_prev2 = ao.shift(2)

    is_green = ao > ao_prev1
    is_red = ao < ao_prev1
    # Bearish saucer pair check (for red-pair test at t-2,t-1): bar t-1 is
    # red relative to t-2, and bar t-2 is red relative to t-3.
    red_pair = (ao_prev1 < ao_prev2) & (ao_prev2 < ao.shift(3))

    bullish_saucer = (ao > 0) & red_pair & is_green

    bearish_saucer_pair = (ao_prev1 > ao_prev2) & (ao_prev2 > ao.shift(3))
    bearish_saucer = (ao < 0) & bearish_saucer_pair & is_red

    zero_cross_down = (ao < 0) & (ao_prev1 >= 0)

    if use_trend_filter:
        sma_trend = close.rolling(trend_window).mean()
        trend_ok = close > sma_trend
        entry = bullish_saucer & trend_ok.fillna(False)
    else:
        entry = bullish_saucer

    exit_signal = zero_cross_down | bearish_saucer

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
