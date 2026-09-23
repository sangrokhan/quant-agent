"""Strategy: Williams %R + CCI dual oversold-threshold confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-025):
Per StockSharp's "Rabbit3" strategy documentation (conversion of a
MetaTrader 5 expert advisor by barabashkakvn,
https://doc.stocksharp.com/api-examples/2540_Rabbit3): long entry requires
Williams %R to be below its oversold threshold (default -80) on BOTH the
current AND previous closed bar, AND CCI to be below its own buy threshold
(default -80) at the same time -- a simultaneous dual-threshold
confirmation (not a crossover) from two independently-constructed
oscillators (Williams %R: close position within N-bar high/low range; CCI:
typical-price deviation from its own moving average, scaled by mean
absolute deviation). First Williams %R + CCI combo in this repo. This
repo's prior Williams %R and CCI entries were tested individually
(threshold/crossover/divergence variants); none combined them into a
simultaneous dual-oversold-confirmation gate. Adapted to this repo's
single-position long-only generate_signals/generate_returns contract by
dropping the source's position-stacking, dynamic profit-based sizing, and
pip-based stop-loss/take-profit mechanics (not applicable to a single 0/1
position series) -- keeping only the core dual-threshold entry logic plus
this repo's standard overbought-threshold exit and max_hold_days time-stop.

Signal logic
------------
- Williams %R(williams_period) = -100 * (highest_high - close) /
  (highest_high - lowest_low), over a rolling williams_period window.
- CCI(cci_period) = (typical_price - SMA(typical_price)) /
  (0.015 * mean_abs_deviation(typical_price)).
- Entry (long): Williams %R < williams_oversold on BOTH the current and
  previous bar, AND CCI < cci_buy_level (both conditions true
  simultaneously).
- Exit: Williams %R crosses above williams_overbought_exit, OR CCI crosses
  above cci_sell_level, OR a max_hold_days time-stop.

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


def _williams_r(df: pd.DataFrame, period: int) -> pd.Series:
    highest_high = df["high"].rolling(period).max()
    lowest_low = df["low"].rolling(period).min()
    wr = -100.0 * (highest_high - df["close"]) / (highest_high - lowest_low).replace(0, pd.NA)
    return wr.fillna(-50.0)


def _cci(df: pd.DataFrame, period: int) -> pd.Series:
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    sma = typical.rolling(period).mean()
    import numpy as np
    mad = typical.rolling(period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    cci = (typical - sma) / (0.015 * mad.replace(0, pd.NA))
    return cci.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    williams_period: int = 62,
    williams_oversold: float = -80.0,
    williams_overbought_exit: float = -20.0,
    cci_period: int = 15,
    cci_buy_level: float = -80.0,
    cci_sell_level: float = 80.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    wr = _williams_r(df, williams_period)
    cci = _cci(df, cci_period)

    wr_oversold_now = wr < williams_oversold
    wr_oversold_prev = wr_oversold_now.shift(1).fillna(False)
    cci_buy = cci < cci_buy_level

    entry = wr_oversold_now & wr_oversold_prev & cci_buy

    exit_signal = (wr > williams_overbought_exit) | (cci > cci_sell_level)

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
