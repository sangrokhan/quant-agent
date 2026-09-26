"""Strategy: SMA(200) trend-following gated by an IBD-style Distribution-Day
cluster kill-switch.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-002):
Per Investor's Business Daily / William O'Neil's CAN SLIM methodology
(summarized at https://grokipedia.com/page/Distribution_day, corroborating
https://ibdstock.com/analyze-distribution-days-market-timing/): a
"Distribution Day" is any session where a major index closes down >=0.2%
on volume higher than the prior session (institutional selling); IBD's own
rule of thumb is that an accumulation of 4-5 distribution days within
roughly a 4-5-week (~20-25 trading day) window signals intensifying
institutional selling pressure and historically precedes market
corrections, warranting a reduction in exposure.

This repo already tested Follow-Through-Day + Distribution-Day as a
STANDALONE entry/exit state machine (2026-09-08-067, rejected decisively,
grid pass_fraction 0/144) -- that prior attempt used distribution days as
part of a multi-state rally-attempt machine mirroring O'Neil's full system.
This iteration tests a structurally different, narrower construction
following this repo's own established "kill-switch overlay on an existing
base trend signal" pattern (per accepted 2026-09-22-002 variance-ratio
kill-switch and accepted 2026-09-22-108 FGI+vol kill-switch): a plain
SMA(200) trend-following base signal, overridden to flat whenever a
rolling window's distribution-day count reaches a threshold, for a
cooldown period. This isolates the distribution-day-cluster designed
"warning signal" as a pure risk-off override rather than embedding it in
O'Neil's full multi-signal rally-attempt state machine.

Signal logic
------------
- distribution_day[t]: close[t] <= close[t-1] * (1 - down_pct) AND
  volume[t] > volume[t-1].
- distribution_count[t] = rolling sum of distribution_day over the
  trailing `window` trading days (IBD convention ~20-25 days).
- Base trend signal: long when close > SMA(trend_window).
- Kill-switch: once distribution_count >= dist_threshold, force flat for
  `cooldown_days` trading days (even if the base trend signal remains
  bullish), then resume respecting the base signal.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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
    trend_window: int = 200,
    down_pct: float = 0.002,
    window: int = 15,
    dist_threshold: int = 6,
    cooldown_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    sma = close.rolling(trend_window, min_periods=trend_window).mean()
    base_signal = (close > sma).fillna(False)

    prev_close = close.shift(1)
    prev_volume = volume.shift(1)
    distribution_day = (close <= prev_close * (1 - down_pct)) & (volume > prev_volume)
    distribution_day = distribution_day.fillna(False)

    dist_count = distribution_day.rolling(window, min_periods=1).sum()

    position = pd.Series(0, index=close.index, dtype=int)
    cooldown_remaining = 0
    for i in range(len(close)):
        if cooldown_remaining > 0:
            position.iloc[i] = 0
            cooldown_remaining -= 1
            # a fresh cluster trigger while already in cooldown resets the clock
            if dist_count.iloc[i] >= dist_threshold:
                cooldown_remaining = cooldown_days
            continue
        if dist_count.iloc[i] >= dist_threshold:
            cooldown_remaining = cooldown_days
            position.iloc[i] = 0
            continue
        position.iloc[i] = 1 if bool(base_signal.iloc[i]) else 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
