"""Strategy: CCI(20) trend-continuation breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-072):
Per TradeAlgo's CCI trading-guide (search-result snippet, page body
JS-lazy-loaded/unrenderable) trend-continuation strategy family: enter long
when CCI crosses above +100 from below (a strong-momentum breakout, distinct
from the classic oversold-threshold mean-reversion CCI variant already
tested and rejected at 2026-09-04-024). Hold the position as long as CCI
stays above zero (a much looser "still trending" condition than the entry
threshold). Exit when CCI drops below zero. This is a trend-following, not
mean-reverting, use of CCI -- opposite economic thesis from -024's
oversold-dip-buy, distinct from Donchian/SMA/EMA trend systems already
tested since CCI measures deviation from a mean-absolute-deviation band
rather than price level or moving-average crossovers.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _cci(df: pd.DataFrame, window: int) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    sma_tp = typical_price.rolling(window).mean()
    # Mean absolute deviation from the rolling mean (Lambert's original
    # formulation), scaled by the standard 0.015 constant.
    mad = typical_price.rolling(window).apply(
        lambda x: abs(x - x.mean()).mean(), raw=True
    )
    cci = (typical_price - sma_tp) / (0.015 * mad)
    return cci


def generate_signals(
    price_df: pd.DataFrame,
    cci_window: int = 20,
    entry_threshold: float = 100.0,
    exit_threshold: float = 0.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: CCI crosses above ``entry_threshold`` (from below).
    Exit: CCI drops below ``exit_threshold`` (much looser than entry, per
    the source's own "hold while CCI stays above zero" rule).
    """
    df = _prep(price_df)
    cci = _cci(df, cci_window)

    cross_up = (cci > entry_threshold) & (cci.shift(1) <= entry_threshold)
    exit_signal = cci < exit_threshold

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        if in_position:
            if bool(exit_signal.iloc[i]) if not pd.isna(exit_signal.iloc[i]) else False:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]) if not pd.isna(cross_up.iloc[i]) else False:
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
