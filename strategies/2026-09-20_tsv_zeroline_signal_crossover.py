"""Strategy: Time Segmented Volume (TSV, Worden Brothers) zero-line + signal crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-079):
Per a Google AI-overview synthesis + QuantifiedStrategies.com's "Time
Segmented Volume (TSV) - Backtest Strategy And Trading Rules" (browser_exec
fallback -- web_search DDGS backend returns mangled non-English results
this iteration), TSV (Worden Brothers Inc.) sums price-change-weighted
volume over a rolling time segment: on up-close days, that day's volume
counts as positive pressure; on down-close days, it counts as negative
pressure. TSV rising above zero and above its own signal-line moving
average indicates buying pressure/accumulation dominates; the disclosed
rule set combines a zero-line crossover with a TSV-vs-signal-line
crossover for entry confirmation. This is a genuinely distinct volume
construction from every existing OBV/PVT/AD-Line/Force-Index strategy in
this repo since TSV explicitly segments and re-sums price-change-weighted
volume over a FIXED ROLLING WINDOW (not a running cumulative total that
never resets) -- making it more responsive to recent accumulation/
distribution shifts than the cumulative volume indicators already tested.
0 prior TSV entries in this repo.

TSV formula (standard, Worden Brothers):
    signed_volume_t = volume_t if close_t > close_{t-1} else -volume_t if close_t < close_{t-1} else 0
    TSV = signed_volume.rolling(segment_period).sum()
    signal = TSV.rolling(signal_period).mean()

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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


def _tsv(close: pd.Series, volume: pd.Series, segment_period: int = 13) -> pd.Series:
    diff = close.diff()
    signed_volume = np.sign(diff).fillna(0.0) * volume
    return signed_volume.rolling(segment_period).sum()


def generate_signals(
    price_df: pd.DataFrame,
    segment_period: int = 13,
    signal_period: int = 13,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: TSV crosses above zero AND TSV is above its own signal-line
    moving average (buying pressure confirmed dominant). Exit: TSV crosses
    back below zero OR crosses back below the signal line, whichever first.
    """
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    tsv = _tsv(close, volume, segment_period=segment_period)
    signal = tsv.rolling(signal_period).mean()

    zero_cross_up = (tsv > 0) & (tsv.shift(1) <= 0)
    above_signal = tsv > signal
    entry = zero_cross_up & above_signal.fillna(False)
    stay = (tsv > 0) & above_signal.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_vals = entry.fillna(False).values
    stay_vals = stay.fillna(False).values

    for i in range(len(close)):
        if in_position:
            if not bool(stay_vals[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
                in_position = True
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
