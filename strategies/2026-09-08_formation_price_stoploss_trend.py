"""Strategy: SMA(200) trend gate + fixed formation-price stop-loss overlay
(per Han, Zhou & Zhu's momentum-crash stop-loss rule).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-178):
Per CXO Advisory's summary of Han, Zhou & Zhu "Taming Momentum Crashes: A
Simple Stop-Loss Strategy" (https://www.cxoadvisory.com/technical-trading/stop-losses-to-avoid-stock-momentum-crashes/),
imposing a stop-loss rule on a conventional cross-sectional momentum
strategy (exit a position when it falls below its FORMATION price by a
fixed percentage threshold within the holding period) dramatically improved
risk-adjusted performance: at a 15% threshold, gross monthly Sharpe rose
from 0.17 to 0.40 and the worst four monthly losses shrank from
(-49.8%,-39.4%,-35.2%,-34.5%) to (-17.4%,-14.8%,-13.8%,-13.1%). The paper
tested 10/15/20% thresholds, all of which improved Sharpe.

Adapted single-asset time-series (this repo has no cross-sectional
decile-momentum universe): use an SMA(trend_window) trend-following entry
signal (long when close > SMA), then overlay a fixed formation-price
stop-loss -- exit immediately (go flat) if close falls below the price at
entry by more than `stop_loss_pct`, re-entering only on the next fresh
SMA-trend signal. This isolates the STOP-LOSS OVERLAY mechanism as the
tested variable on top of an already-familiar trend filter (same base
signal used by prior position-sizing-overlay entries 2026-09-08-165/174/
175/176), directly testing the source's "does a hard percentage stop-loss
from formation/entry price improve a trend strategy's risk profile"
mechanism rather than its cross-sectional momentum-decile construction.

First fixed-percentage formation-price stop-loss overlay entry in this
repo -- distinct from the CPPI running-max-drawdown-floor overlay
(2026-09-08-174/175, a continuous multiplier-based sizing rule referencing
the PORTFOLIO's own running max) and the vol-targeting overlay
(2026-09-08-165, continuous inverse-vol sizing) since this is a hard
binary exit trigger referenced to each individual TRADE's own entry price,
matching the source paper's exact mechanism.

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


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    stop_loss_pct: float = 0.15,
) -> pd.Series:
    """Return a {0,1} long/flat position series: SMA trend entry, hard
    formation-price stop-loss exit (per Han/Zhou/Zhu), re-entry only on a
    fresh trend signal after a stop-out."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    uptrend = close > sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_price = None

    for i in range(len(close)):
        px = close.iloc[i]
        if in_position:
            stop_price = entry_price * (1.0 - stop_loss_pct)
            trend_flip = not bool(uptrend.iloc[i])
            stopped_out = px < stop_price
            if stopped_out or trend_flip:
                in_position = False
                entry_price = None
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(uptrend.iloc[i]):
                in_position = True
                entry_price = px
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
