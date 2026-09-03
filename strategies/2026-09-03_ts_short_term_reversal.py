"""Strategy: Time-series (single-asset) short-term reversal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-009):
Source: https://quantpedia.com/strategies/short-term-reversal-in-stocks --
the well-documented cross-sectional short-term reversal anomaly (stocks with
low trailing weekly/monthly returns earn positive abnormal returns the
following week, and vice versa; attributed to investor overreaction and
correction, and/or compensation for liquidity provision per Nagel's
"Evaporating Liquidity"). That specific strategy is a cross-sectional
decile-sort across a broad stock universe (buy recent losers, sell recent
winners, large-cap only to survive costs) -- not directly implementable here
since data/loaders.py only fetches single symbols, not a scannable universe.

This strategy adapts the same overreaction/liquidity-provision logic to a
**single-asset time-series** form, distinct from every prior entry in this
log: after a short trailing window (`lookback_days`) of NEGATIVE cumulative
return, go long for the next `hold_days` (betting on mean-reversion/bounce);
otherwise stay flat. This is different from 2026-09-03-001 (Bollinger Band
mean-reversion, which uses a band-distance trigger + vol-regime gate) and
from all momentum strategies (002/003/004, which bet WITH the trailing
return sign, not against it) -- here we bet explicitly AGAINST the trailing
return sign, i.e. the opposite hypothesis to time-series momentum, and only
over a short (day-scale, not 45-200 day) lookback window.

Signal logic
------------
- Trailing signal: cumulative log return over the prior `lookback_days`
  trading days (excluding today, shift(1)).
- Entry (long): trailing cumulative return < -`entry_threshold` (a
  meaningfully negative short-term move).
- Hold: stay long for exactly `hold_days` trading days after entry (fixed
  holding period, not indefinite -- reversal edges are short-lived per the
  source's liquidity-provision framing), then re-evaluate.
- Flat otherwise; long-only, no shorts (per SAFETY.md / prior loop
  convention).

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


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 5,
    entry_threshold: float = 0.03,
    hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    trailing_cum_ret = (close / close.shift(lookback_days) - 1.0).shift(1)
    entry_trigger = trailing_cum_ret < -entry_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
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
