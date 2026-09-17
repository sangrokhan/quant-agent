"""Strategy: Apirine AMA/KAMA crossover (Vitali Apirine, TASC Apr 2018).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-149):
Vitali Apirine's TASC Apr 2018 article "Adaptive Moving Averages" introduces
a NEW adaptive moving average (AMA, distinct from Kaufman's own KAMA) whose
smoothing constant is derived from where the close sits within the recent
high-low RANGE (not from Kaufman's trend-efficiency ratio):
    MLTP = |(Close - Lowest(Low, N+1)) - (Highest(High, N+1) - Close)|
           / (Highest(High, N+1) - Lowest(Low, N+1))
    SSC = MLTP * (FastSC - SlowSC) + SlowSC   (FastSC=2/3, SlowSC=2/31 by default)
    CST = SSC^2
    AMA[t] = AMA[t-1] + CST * (Close - AMA[t-1])
The source's own disclosed TradeStation strategy trades the CROSSOVER
between this new AMA and the classic Kaufman KAMA (same Periods/FastAvgLength/
SlowAvgLength inputs, standard efficiency-ratio-based smoothing): long when
AMA crosses over KAMA, short when AMA crosses under KAMA. Author's own
rationale: "the combination may reduce the number of whipsaws relative to
using either moving average by itself" -- i.e. this is explicitly NOT just
another KAMA-alone strategy (already tested 4+ times in this repo,
2026-09-04-048/120/151, 2026-09-06-181/183) but a two-adaptive-MA crossover
where the two lines use DIFFERENT adaptation mechanisms (range-position vs
efficiency-ratio) and therefore diverge/converge in economically meaningful
ways distinct from any single-MA approach.

Long-only adaptation of source's bidirectional strategy (SellShort branch
dropped per SAFETY.md). Source's own strategy has no explicit exit other
than the reverse crossover -- a max_hold_days time-stop is our own addition
(flagged as such).

Source: https://traders.com/Documentation/FEEDbk_docs/2018/04/TradersTips.html
(TradeStation section, read via browser_exec).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _apirine_ama(
    close: pd.Series, high: pd.Series, low: pd.Series,
    periods: int, fast_avg_length: int, slow_avg_length: int,
) -> pd.Series:
    """Apirine's Adaptive Moving Average (range-position-based smoothing)."""
    pds = periods + 1
    fast_sc = 2.0 / (fast_avg_length + 1)
    slow_sc = 2.0 / (slow_avg_length + 1)

    highest = high.rolling(pds).max()
    lowest = low.rolling(pds).min()
    rng = (highest - lowest).replace(0, float("nan"))

    mltp = ((close - lowest) - (highest - close)).abs() / rng
    ssc = mltp * (fast_sc - slow_sc) + slow_sc
    cst = ssc ** 2

    n = len(close)
    vals = close.to_numpy(dtype=float)
    cst_vals = cst.to_numpy(dtype=float)
    ama = [0.0] * n
    for i in range(n):
        if i == 0:
            ama[i] = vals[i]
            continue
        c = cst_vals[i]
        if c != c:  # NaN guard
            c = slow_sc ** 2
        ama[i] = ama[i - 1] + c * (vals[i] - ama[i - 1])
    return pd.Series(ama, index=close.index)


def _kaufman_kama(
    close: pd.Series, periods: int, fast_avg_length: int, slow_avg_length: int,
) -> pd.Series:
    """Classic Kaufman KAMA (efficiency-ratio-based smoothing)."""
    fast_sc = 2.0 / (fast_avg_length + 1)
    slow_sc = 2.0 / (slow_avg_length + 1)

    change = (close - close.shift(periods)).abs()
    volatility = (close - close.shift(1)).abs().rolling(periods).sum()
    er = (change / volatility.replace(0, float("nan"))).fillna(0.0)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    n = len(close)
    vals = close.to_numpy(dtype=float)
    sc_vals = sc.to_numpy(dtype=float)
    kama = [0.0] * n
    for i in range(n):
        if i == 0:
            kama[i] = vals[i]
            continue
        kama[i] = kama[i - 1] + sc_vals[i] * (vals[i] - kama[i - 1])
    return pd.Series(kama, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    periods: int = 10,
    fast_avg_length: int = 2,
    slow_avg_length: int = 30,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    ama = _apirine_ama(close, high, low, periods, fast_avg_length, slow_avg_length)
    kama = _kaufman_kama(close, periods, fast_avg_length, slow_avg_length)

    cross_over = (ama > kama) & (ama.shift(1) <= kama.shift(1))
    cross_under = (ama < kama) & (ama.shift(1) >= kama.shift(1))

    entry = cross_over.fillna(False)
    exit_cross = cross_under.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or held >= max_hold_days:
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
