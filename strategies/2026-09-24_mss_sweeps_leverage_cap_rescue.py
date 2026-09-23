"""Strategy: MSS Sweeps (BOS-protected-level sweep-and-reclaim) with a
leverage_cap parameter -- rescue attempt for the ETH/USDT near-miss
recorded this same cron trigger (2026-09-24-049: Sharpe 1.147 PASSED,
but MDD 0.356 decisively failed the 0.25 threshold at leverage_cap
implicitly 1.0/full exposure).

Hypothesis (knowledge_base id TBD, this cron trigger):
Direct rescue of this cron trigger's own near-miss 2026-09-24-049 (MSS
Sweeps BOS-protected-level sweep-reclaim, ETH/USDT swing_window=8/
max_hold_days=20: Sharpe 1.147 passed, TC-survival passed, but MDD 0.356
decisively failed, and parameter_sensitivity also failed at 0.557).
Applies this repo's established leverage-cap-recalibration rescue pattern
(previously successful for BOS/Elder-Ray/Chaikin-Oscillator/Twiggs-Money-
Flow/Ultimate-Oscillator and, this same cron trigger, the BOS BTC/USDT
rescue at leverage_cap=0.7): scales the position size down by a fixed
leverage_cap multiplier, directly reducing both the Sharpe numerator's
volatility contribution and drawdown magnitude proportionally, while
searching whether a lower per-trade exposure both clears the MDD threshold
AND keeps the Sharpe far enough above 1.0 to survive the scaling (Sharpe
of a scaled position series is leverage-invariant EXCEPT for the fixed
per-trade cost drag in check_transaction_cost_survival, which does NOT
scale down with leverage_cap, so smaller leverage_cap can only help MDD,
never Sharpe directly -- this is a genuine drawdown-vs-return trade-off
test, not a free lunch).

Signal logic
------------
Identical entry/exit/pivot-detection logic to
strategies/2026-09-24_mss_sweeps_protected_level_reclaim.py, but every
non-zero position value is scaled by `leverage_cap` (e.g. leverage_cap=0.5
means half-size positions) instead of always being exactly 1.0/full size.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


def _pivot_highs_lows(df: pd.DataFrame, swing_window: int):
    high = df["high"]
    low = df["low"]
    window = 2 * swing_window + 1
    rolling_max = high.rolling(window, center=True).max()
    rolling_min = low.rolling(window, center=True).min()
    is_pivot_high_raw = (high == rolling_max)
    is_pivot_low_raw = (low == rolling_min)
    is_pivot_high = is_pivot_high_raw.shift(swing_window).fillna(False).astype(bool)
    is_pivot_low = is_pivot_low_raw.shift(swing_window).fillna(False).astype(bool)
    return is_pivot_high, is_pivot_low


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 8,
    max_hold_days: int = 20,
    trend_window: int = 200,
    trend_filter: bool = True,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a leverage_cap-scaled long/flat position series (0 or leverage_cap)."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    n = len(df)

    is_pivot_high, is_pivot_low = _pivot_highs_lows(df, swing_window)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False) if trend_filter else pd.Series(True, index=close.index)

    position = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    entry_idx = 0

    last_swing_high = None
    last_swing_low = None
    protected_level = None
    bos_confirmed = False

    i = swing_window
    while i < n:
        if bool(is_pivot_high.iloc[i]):
            last_swing_high = high.iloc[i]
        if bool(is_pivot_low.iloc[i]):
            last_swing_low = low.iloc[i]
            if bos_confirmed:
                protected_level = last_swing_low

        if last_swing_high is not None and close.iloc[i] > last_swing_high and not bos_confirmed:
            bos_confirmed = True
            protected_level = last_swing_low

        if in_position:
            held = i - entry_idx
            invalidated = protected_level is not None and close.iloc[i] < protected_level
            if invalidated or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0.0
                i += 1
                continue
            position.iloc[i] = leverage_cap
            i += 1
            continue

        if (
            bos_confirmed
            and protected_level is not None
            and bool(uptrend.iloc[i])
            and low.iloc[i] < protected_level
            and close.iloc[i] > protected_level
        ):
            in_position = True
            entry_idx = i
            position.iloc[i] = leverage_cap
            i += 1
            continue

        position.iloc[i] = 0.0
        i += 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
