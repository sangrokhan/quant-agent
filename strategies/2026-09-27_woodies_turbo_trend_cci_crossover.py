"""Strategy: Woodie's CCI Turbo/Trend dual-line crossover, trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Woodie's CCI trading system (Ken Wood) explicitly separates a fast "Turbo
CCI" (period 6) from the slower "Trend CCI" (period 14 for sub-60-minute
bars, period 20 for higher timeframes -- daily bars here use 20 per the
source's own timeframe convention) -- per
https://ftmo.com/en/blog/woodies-cci-system/ (visited this iteration):
"Turbo CCI: with period 6" and "Trend CCI ... period of 20 for time frames
higher than 60 minutes." The source's own trend definition is "six lines
[bars] above the Zero-Line" = established uptrend.

This repo has 5+ prior Woodie's CCI entries (Zero-Line-Reject, Trend-Line-
Break, Hook-From-Extreme, Woodie Pivot Points, Pivot Point continuous-sizing
dial) but NONE use this specific Turbo-vs-Trend dual-line construction --
genuinely distinct signal mechanism (a fast/slow CCI crossover, analogous to
a MACD-style dual-moving-average cross but on the CCI oscillator itself,
rather than a single-line threshold/pattern trigger).

Signal logic
------------
- Trend CCI (period `trend_period`, default 20) must have been above zero
  for at least `trend_established_bars` consecutive bars (source's "six
  lines above the Zero-Line" uptrend definition) -- this is the regime gate.
- Turbo CCI (period `turbo_period`, default 6) crossing from below to above
  the Trend CCI, while both are positive (uptrend context), signals a fresh
  momentum acceleration worth a long entry.
- Exit: Turbo CCI crosses back below Trend CCI, OR Trend CCI itself drops
  below zero (regime break), OR a `max_hold_days` time-stop.

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


def _cci(df: pd.DataFrame, period: int) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    sma = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: (x - x.mean()).abs().mean(), raw=False)
    cci = (tp - sma) / (0.015 * mad.replace(0, pd.NA))
    return cci.astype(float)


def generate_signals(
    price_df: pd.DataFrame,
    turbo_period: int = 6,
    trend_period: int = 20,
    trend_established_bars: int = 6,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)

    turbo_cci = _cci(df, turbo_period)
    trend_cci = _cci(df, trend_period)

    trend_positive = trend_cci > 0
    # "six lines above zero" -- trend_established requires the trailing
    # trend_established_bars bars (inclusive of current) to all be positive.
    trend_established = (
        trend_positive.rolling(trend_established_bars).sum() >= trend_established_bars
    )

    cross_up = (turbo_cci > trend_cci) & (turbo_cci.shift(1) <= trend_cci.shift(1))
    cross_down = (turbo_cci < trend_cci) & (turbo_cci.shift(1) >= trend_cci.shift(1))

    entry = cross_up & trend_established.fillna(False) & trend_positive.fillna(False)
    exit_cross = cross_down
    exit_regime = ~trend_positive.fillna(False)

    close = df["close"]
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or bool(exit_regime.iloc[i]) or held >= max_hold_days:
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
