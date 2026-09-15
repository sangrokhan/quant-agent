"""Strategy: KDJ oversold golden-cross mean-reversion entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-001):
Per https://blog.itick.io/en/technical-analysis/kdj-trading-strategies
("Overbought/Oversold Strategy": buy when K, D, J are all below 20 (oversold
zone) AND K crosses above D (golden cross); sell/exit when K, D, J are all
above 80 (overbought zone) AND K crosses below D (death cross)). KDJ is a
stochastic-oscillator derivative: %K/%D are the standard fast/slow
stochastic lines, %J = 3*%K - 2*%D (an amplified, more volatile third line
used to flag extremes earlier than %K/%D alone). This is the FIRST KDJ
strategy tested in this repo (grep of strategies_index.jsonl returned zero
prior KDJ entries) -- distinct from the many prior plain-Stochastic and
Stochastic-RSI entries because the %J line's amplification changes both
entry timing and the all-three-lines-below/above-threshold condition.

Signal logic
------------
- Raw stochastic %K (rsv) over `k_window` days: (close - lowest_low) /
  (highest_high - lowest_low) * 100.
- %K = k_smooth-period SMA-smoothed RSV (source uses a smoothing EMA/SMA of
  the raw stochastic; use simple rolling mean here for determinism).
- %D = d_smooth-period SMA of %K.
- %J = 3*%K - 2*%D.
- Entry (long): all of K, D, J < oversold_thresh (default 20) on the prior
  bar's close, AND K crosses above D (golden cross) today.
- Exit: all of K, D, J > overbought_thresh (default 80) AND K crosses below
  D (death cross), OR a max holding period of `max_hold_days` (source
  doesn't specify a hard time-stop; added here to avoid indefinite holds
  when KDJ never re-reaches overbought, consistent with this repo's other
  KDJ-adjacent oscillator strategies).

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


def _kdj(df: pd.DataFrame, k_window: int, k_smooth: int, d_smooth: int):
    low_min = df["low"].rolling(k_window).min()
    high_max = df["high"].rolling(k_window).max()
    rng = (high_max - low_min).replace(0, pd.NA)
    rsv = ((df["close"] - low_min) / rng * 100).fillna(50.0)
    k = rsv.rolling(k_smooth).mean()
    d = k.rolling(d_smooth).mean()
    j = 3 * k - 2 * d
    return k, d, j


def generate_signals(
    price_df: pd.DataFrame,
    k_window: int = 9,
    k_smooth: int = 3,
    d_smooth: int = 3,
    oversold_thresh: float = 20.0,
    overbought_thresh: float = 80.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    k, d, j = _kdj(df, k_window, k_smooth, d_smooth)

    prior_oversold = (
        (k.shift(1) < oversold_thresh)
        & (d.shift(1) < oversold_thresh)
        & (j.shift(1) < oversold_thresh)
    )
    golden_cross = (k.shift(1) <= d.shift(1)) & (k > d)
    entry = (prior_oversold.fillna(False)) & golden_cross.fillna(False)

    prior_overbought = (
        (k.shift(1) > overbought_thresh)
        & (d.shift(1) > overbought_thresh)
        & (j.shift(1) > overbought_thresh)
    )
    death_cross = (k.shift(1) >= d.shift(1)) & (k < d)
    exit_signal = (prior_overbought.fillna(False)) & death_cross.fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    idx = df.index
    for i in range(len(idx)):
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
