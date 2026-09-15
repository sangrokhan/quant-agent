"""Strategy: Kaufman Adaptive Moving Average (KAMA) trend crossover
(long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's
id): per Kaufman's KAMA construction (Google AI-overview synthesis of
PyQuantLab/StockCharts/TradingView/Stonehill Forex/Medium/ChartMini), KAMA
adapts its smoothing speed via the Efficiency Ratio (ER = |net price
change over er_period| / sum(|bar-to-bar changes|)), blending fast/slow EMA
constants so it hugs price closely during clean trends and flattens during
chop. Distinct from this repo's extensive prior Kaufman Efficiency Ratio
(KER) work (12+ entries, e.g. 2026-09-14-111/2026-09-16-072) which used ER
directly as a CONTINUOUS POSITION-SIZING DIAL within an SMA-trend gate --
this strategy instead builds the actual KAMA adaptive-smoothing LINE and
trades a CROSSOVER signal against it (price crosses above/below the KAMA
line itself), a fundamentally different signal mechanism from a raw ER
dial. Long entry: close crosses above KAMA (source's own entry rule). Exit:
close crosses below KAMA, or falls below KAMA - atr_buffer_mult*ATR(14)
(source's own noted "ATR buffer beneath KAMA to prevent premature whipsaw
exits" refinement), or a max_hold_days time-stop.

Sources read this iteration:
- Google AI-overview synthesis of KAMA trading strategy entry/exit rules
  (PyQuantLab, StockCharts, TradingView, Stonehill Forex, ChartMini,
  Darwinex).

Signal logic
------------
- Efficiency Ratio: ER_t = |close_t - close_{t-er_period}| / sum(|close_i -
  close_{i-1}| for i in (t-er_period, t])  (Kaufman's original formula).
- Smoothing Constant: SC_t = (ER_t * (2/(fast_period+1) - 2/(slow_period+1))
  + 2/(slow_period+1)) ** 2.
- KAMA_t = KAMA_{t-1} + SC_t * (close_t - KAMA_{t-1}).
- Long entry: close crosses above KAMA (prev close <= prev KAMA, current
  close > current KAMA).
- Exit: close crosses below (KAMA - atr_buffer_mult*ATR(14)) (buffered
  exit per source's own whipsaw-reduction refinement), or a max_hold_days
  time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _kama(close: pd.Series, er_period: int, fast_period: int, slow_period: int) -> pd.Series:
    n = len(close)
    kama = pd.Series(index=close.index, dtype=float)
    close_np = close.to_numpy()

    change = np.abs(close_np - np.roll(close_np, er_period))
    change[:er_period] = np.nan
    diff_abs = np.abs(np.diff(close_np, prepend=close_np[0]))
    volatility = pd.Series(diff_abs).rolling(er_period).sum().to_numpy()

    with np.errstate(divide="ignore", invalid="ignore"):
        er = np.where(volatility > 0, change / volatility, 0.0)

    fast_sc = 2.0 / (fast_period + 1)
    slow_sc = 2.0 / (slow_period + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    first_valid = er_period
    if first_valid >= n:
        return kama
    kama_np = np.full(n, np.nan)
    kama_np[first_valid] = close_np[first_valid]
    for i in range(first_valid + 1, n):
        kama_np[i] = kama_np[i - 1] + sc[i] * (close_np[i] - kama_np[i - 1])
    kama[:] = kama_np
    return kama


def generate_signals(
    price_df: pd.DataFrame,
    er_period: int = 10,
    fast_period: int = 2,
    slow_period: int = 30,
    atr_buffer_mult: float = 1.0,
    max_hold_days: int = 40,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    atr = _atr(df, 14)

    kama = _kama(close, er_period, fast_period, slow_period)

    prev_close = close.shift(1)
    prev_kama = kama.shift(1)
    cross_up = (prev_close <= prev_kama) & (close > kama)

    n = len(df.index)
    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_days = 0

    for i in range(n):
        c = close.iloc[i]
        k = kama.iloc[i]
        a = atr.iloc[i]
        if pd.isna(k):
            continue

        if in_position:
            hold_days += 1
            exit_level = k - atr_buffer_mult * a if not pd.isna(a) else k
            if c < exit_level or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
            else:
                position.iloc[i] = 1
                continue

        if bool(cross_up.iloc[i]):
            in_position = True
            hold_days = 1
            position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    er_period: int = 10,
    fast_period: int = 2,
    slow_period: int = 30,
    atr_buffer_mult: float = 1.0,
    max_hold_days: int = 40,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        er_period=er_period,
        fast_period=fast_period,
        slow_period=slow_period,
        atr_buffer_mult=atr_buffer_mult,
        max_hold_days=max_hold_days,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
