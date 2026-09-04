"""Strategy: Relative Vigor Index (RVI) signal-line crossover at momentum extremes.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-130):
The Relative Vigor Index (RVI) measures price momentum via the tendency of
close to finish above open in an uptrend / below open in a downtrend,
normalized by the bar's trading range, then smoothed with a 4-bar weighted
average (numerator/denominator each a symmetric [1,2,2,1]/6 weighted sum
over the current + 3 prior bars) and an n-period SMA. A signal line is a
similarly-weighted 4-bar average of the RVI itself. Per
quantifiedstrategies.com: "if the indicator is far below the centerline and
the RVI line crosses above the signal line, it indicates a shift in
momentum from bearish to bullish... if the indicator is far above the
centerline and the RVI line crosses below the signal line, it indicates a
potential shift from bullish to bearish." This strategy operationalizes
that "at momentum extremes" qualifier as a fixed threshold band: long entry
when RVI crosses above its signal line while RVI < -entry_threshold
(oversold zone); exit when RVI crosses below signal (mirroring the source's
symmetric sell rule) or a max_hold_days time-stop. First RVI strategy
tested in this repo -- distinct from all prior open/close-vs-range
oscillators (BOP uses (close-open)/(high-low) unsmoothed per-bar; Elder Ray
Bull/Bear Power uses EMA-relative highs/lows) due to RVI's specific
4-bar-weighted double-smoothing construction.

Signal logic
------------
- period: SMA smoothing period for RVI numerator/denominator (default 10).
- entry_threshold: RVI must be below -entry_threshold (oversold zone,
  in RVI's roughly -1..+1 range) for a crossover to count as a valid
  entry (default 0.2).
- Long entry: RVI crosses above signal line AND RVI < -entry_threshold.
- Exit: RVI crosses below signal line, OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _weighted4(s: pd.Series) -> pd.Series:
    """Symmetric [1,2,2,1]/6 weighted sum of current bar + 3 prior bars."""
    return (s + 2 * s.shift(1) + 2 * s.shift(2) + s.shift(3)) / 6.0


def _rvi(df: pd.DataFrame, period: int) -> tuple[pd.Series, pd.Series]:
    co = df["close"] - df["open"]
    hl = df["high"] - df["low"]

    num_w = _weighted4(co)
    den_w = _weighted4(hl)

    num_sma = num_w.rolling(period).mean()
    den_sma = den_w.rolling(period).mean()

    rvi = num_sma / den_sma.replace(0, pd.NA)
    signal = _weighted4(rvi)
    return rvi, signal


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 10,
    entry_threshold: float = 0.2,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)

    rvi, signal = _rvi(df, period)

    cross_up = (rvi > signal) & (rvi.shift(1) <= signal.shift(1))
    cross_down = (rvi < signal) & (rvi.shift(1) >= signal.shift(1))
    oversold = rvi < -entry_threshold

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = bool(cross_down.iloc[i]) if pd.notna(cross_down.iloc[i]) else False
            if exit_now or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entry_cross = bool(cross_up.iloc[i]) if pd.notna(cross_up.iloc[i]) else False
            entry_zone = bool(oversold.iloc[i]) if pd.notna(oversold.iloc[i]) else False
            if entry_cross and entry_zone:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 10,
    entry_threshold: float = 0.2,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, period=period, entry_threshold=entry_threshold, max_hold_days=max_hold_days
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
