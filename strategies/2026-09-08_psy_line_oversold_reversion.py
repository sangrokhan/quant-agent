"""Strategy: Psychological Line (PSY) oversold mean-reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
per https://www.investchannels.com/psychological-line-indicator-trading-strategies-and-tips/,
the Psychological Line (PSY) is a simple sentiment oscillator: the
percentage of the last N bars that closed higher than the prior bar's
close (0-100 scale, distinct from RSI/Stochastic which weight by magnitude
of the move, not just its direction). Readings above 70 are "overbought"
(likely reversal down), below 30 are "oversold" (likely reversal up).
This strategy trades the oversold-mean-reversion side: when PSY drops
below a low threshold (market has had very few up-closes recently,
suggesting selling exhaustion), go long expecting a bounce back toward
the 50 (balanced) level.

Signal logic
------------
- PSY(psy_period) = 100 * count(close_t > close_{t-1} for the last
  psy_period bars) / psy_period.
- Entry (long): PSY crosses below oversold_threshold (default 30).
- Exit: PSY reverts back above exit_threshold (default 50, the "balanced"
  midline per the source's own trend-following interpretation), or a
  max_hold_days time-stop.
- Flat otherwise.

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


def _psy(close: pd.Series, psy_period: int) -> pd.Series:
    up_close = (close.diff() > 0).astype(float)
    return 100.0 * up_close.rolling(psy_period).sum() / psy_period


def generate_signals(
    price_df: pd.DataFrame,
    psy_period: int = 12,
    oversold_threshold: float = 30.0,
    exit_threshold: float = 50.0,
    max_hold_days: int = 10,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    psy = _psy(close, psy_period)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_days = 0
    for i in range(len(df.index)):
        p = psy.iloc[i]
        if in_position:
            hold_days += 1
            if pd.isna(p) or p >= exit_threshold or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
            else:
                position.iloc[i] = 1
        else:
            if not pd.isna(p) and p <= oversold_threshold:
                in_position = True
                hold_days = 1
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    psy_period: int = 12,
    oversold_threshold: float = 30.0,
    exit_threshold: float = 50.0,
    max_hold_days: int = 10,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        psy_period=psy_period,
        oversold_threshold=oversold_threshold,
        exit_threshold=exit_threshold,
        max_hold_days=max_hold_days,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
