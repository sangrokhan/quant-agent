"""Strategy: Kaufman Adaptive Moving Average (KAMA) crossover, slope-confirmed.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-048):
Per a Google AI-overview synthesis (Definedge Securities / Darwinex /
Arrow Algo et al.): the Kaufman Adaptive Moving Average (KAMA, Perry
Kaufman) is a moving average whose smoothing constant self-adjusts based
on an Efficiency Ratio (ER) -- speeding up in smooth trending conditions,
slowing down in choppy/noisy conditions -- a fundamentally different
construction from every fixed-window MA already tested in this repo.
Standard params: ER period=10, fast EMA constant=2, slow EMA constant=30.
Buy entry: price closes above the KAMA line AND KAMA's own slope is
rising (KAMA_t > KAMA_{t-1}). Exit: price closes back below a
flattening/falling KAMA.

KAMA formula (standard, Kaufman 1998):
    Efficiency Ratio (ER) = |price_t - price_{t-er_period}| / sum(|price_i - price_{i-1}|, er_period)
    fast_sc = 2 / (fast_ema_const + 1)
    slow_sc = 2 / (slow_ema_const + 1)
    SC = (ER * (fast_sc - slow_sc) + slow_sc) ** 2
    KAMA_t = KAMA_{t-1} + SC * (price_t - KAMA_{t-1})

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


def _kama(
    close: pd.Series,
    er_period: int = 10,
    fast_ema_const: int = 2,
    slow_ema_const: int = 30,
) -> pd.Series:
    change = (close - close.shift(er_period)).abs()
    volatility = close.diff().abs().rolling(er_period).sum()
    er = (change / volatility.replace(0, pd.NA)).fillna(0.0)

    fast_sc = 2.0 / (fast_ema_const + 1)
    slow_sc = 2.0 / (slow_ema_const + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    kama = pd.Series(index=close.index, dtype=float)
    first_valid = close.first_valid_index()
    kama.loc[first_valid] = close.loc[first_valid]
    idx_list = list(close.index)
    start_pos = idx_list.index(first_valid)
    for i in range(start_pos + 1, len(idx_list)):
        prev_idx = idx_list[i - 1]
        cur_idx = idx_list[i]
        prev_kama = kama.loc[prev_idx]
        if pd.isna(prev_kama):
            kama.loc[cur_idx] = close.loc[cur_idx]
            continue
        sc_val = sc.loc[cur_idx] if pd.notna(sc.loc[cur_idx]) else slow_sc ** 2
        kama.loc[cur_idx] = prev_kama + sc_val * (close.loc[cur_idx] - prev_kama)
    return kama


def generate_signals(
    price_df: pd.DataFrame,
    er_period: int = 10,
    fast_ema_const: int = 2,
    slow_ema_const: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    kama = _kama(close, er_period=er_period, fast_ema_const=fast_ema_const,
                 slow_ema_const=slow_ema_const)
    kama_rising = kama > kama.shift(1)

    price_above_kama = close > kama
    entry = price_above_kama & kama_rising.fillna(False)
    stay = price_above_kama  # exit when price closes back below KAMA

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if not bool(stay.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
