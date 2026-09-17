"""Strategy: Golden Triangle pullback-pivot confirmation (Charlotte Hudgin,
TASC September 2014, "Finding The Golden Triangle"), read this iteration via
browser_exec at https://traders.com/Documentation/FEEDbk_docs/2014/09/TradersTips.html
(TradeStation EasyLanguage code disclosed directly in the article's Traders'
Tips section, after web_search DDGS backend errored on this query -- Google
search fallback used for keyword discovery).

Hypothesis (see knowledge_base/strategies_log.jsonl id for this entry):
A fast-growing stock that pauses (pulls back to its own N-day SMA after a
confirmed swing-high pivot, with "whitespace" between price and its MA
widening on a linear-regression basis, i.e. the pullback is orderly/shallow
rather than violent) and then resumes upward on above-average volume is
likely to continue its prior uptrend. This is a discrete 3-phase STATE
MACHINE (WaitingForPivot -> WaitingForPullback -> WaitingForConfirm ->
signal), not a continuous indicator -- distinct from every other pivot-based
strategy in this repo (Pivot Point SuperTrend, Fibonacci pivots, classic
Pivot Points) because those anchor a trailing band/level to the pivot, while
Golden Triangle uses the pivot only as a state-transition trigger inside a
strict multi-step confirmation sequence with its own timeouts at each phase.
First Golden-Triangle-pattern strategy in this repo.

Exact rule set (translated from Hudgin/TASC's EasyLanguage, faithfully
reproducing state semantics and phase timeouts):
    MAValue = SMA(Close, avg_length)
    PriceDiff = Close - MAValue
    Phase 1 (WaitingForPivot): a confirmed swing-high pivot (strength =
        pivot_strength bars on each side, i.e. a local high with
        pivot_strength lower highs immediately before AND after it) that also
        satisfies "whitespace increasing": at the pivot bar, Close was above
        its MA AND the linear-regression slope of PriceDiff over the last 20
        bars (ending at the pivot) exceeds the linear-regression slope of
        PriceDiff over the prior 20-bar window before that (i.e. price is
        pulling away from its MA faster now than it was 20 bars earlier).
        On confirmation -> record PivotBar/PivotPrice, move to Phase 2.
    Phase 2 (WaitingForPullback): timeout after 20 bars since the pivot (back
        to Phase 1, no signal). Otherwise, once Low <= MAValue (price
        pulls back to touch/cross its MA):
          - if the pullback happened within 3 bars of the pivot -> treat as
            an immediate/sharp pullback, go straight to Phase 3
            (WaitingForConfirm).
          - else, check whether volume was "increasing" (above its own
            avg_length-day average on >=50% of the bars since the pivot);
            if so this is judged a false/overextended setup -> abandon, back
            to Phase 1; if not, proceed to Phase 3.
    Phase 3 (WaitingForConfirm): timeout after 15 bars since the pullback OR
        if Close > PivotPrice * 1.05 (already broke out too far without
        volume confirmation) -> abandon, back to Phase 1, no signal.
        Otherwise, a LONG entry signal fires on the first bar where (this is
        the first bar of the pullback OR Close > Close[1]) AND Close >
        MAValue AND Volume > VolumeAvg * vol_confirm_mult (volume
        confirmation) -> "SignalConfirmed", go long, reset to Phase 1
        watching for the next setup.

Exit: since Hudgin's article (per TASC's own Traders' Tips writeup) does not
specify an exit and TASC's own TradeStation code explicitly leaves exit
choice to the user/built-in strategies, this implementation exits on a
max_hold_days time-stop OR when Close falls back below MAValue (the same MA
that defined the setup), whichever comes first -- a conservative,
mechanical choice consistent with the entry's own trend-following premise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _lin_reg_slope(series: pd.Series, window: int) -> pd.Series:
    """Rolling linear-regression slope (least squares) over `window` bars."""
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    denom = ((x - x_mean) ** 2).sum()

    def _slope(vals: np.ndarray) -> float:
        y_mean = vals.mean()
        num = ((x - x_mean) * (vals - y_mean)).sum()
        return num / denom if denom != 0 else 0.0

    return series.rolling(window).apply(_slope, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    avg_length: int = 50,
    pivot_strength: int = 3,
    slope_window: int = 20,
    pullback_timeout: int = 20,
    confirm_timeout: int = 15,
    breakout_cap_pct: float = 0.05,
    vol_confirm_mult: float = 1.1,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series per the Golden Triangle rule."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    n = len(df)

    ma_value = close.rolling(avg_length).mean()
    price_diff = close - ma_value
    vol_avg = volume.rolling(avg_length).mean()

    # Rolling swing-high pivot: a bar whose High is the max over
    # [-pivot_strength, +pivot_strength] window (confirmed pivot_strength
    # bars later).
    roll_max = high.rolling(2 * pivot_strength + 1, center=True).max()
    is_pivot_high = (high == roll_max) & high.notna() & roll_max.notna()

    # "Whitespace increasing" test at a pivot bar i (needs slope_window*2
    # history before i): slope of price_diff over [i-slope_window+1, i]
    # (ending at pivot, i.e. PriceDiff[PivotStrength] in EasyLanguage terms
    # translates here to using data up to the pivot bar) exceeds slope over
    # the prior slope_window window before that.
    slope_recent = _lin_reg_slope(price_diff, slope_window)
    slope_prior = slope_recent.shift(slope_window)

    close_above_ma_at_pivot = close > ma_value

    state = 0  # 0 = waiting_for_pivot, 1 = waiting_for_pullback, 2 = waiting_for_confirm, 3 = in_position
    pivot_bar = -1
    pivot_price = 0.0
    pullback_bar = -1
    entry_bar = -1

    position = np.zeros(n, dtype=int)

    close_vals = close.values
    low_vals = low.values
    high_vals = high.values
    vol_vals = volume.values
    vol_avg_vals = vol_avg.values
    ma_vals = ma_value.values
    is_pivot_vals = is_pivot_high.values
    slope_recent_vals = slope_recent.values
    slope_prior_vals = slope_prior.values
    above_ma_vals = close_above_ma_at_pivot.values

    for i in range(n):
        if state == 3:
            # manage open position: exit on close < MA or max_hold_days
            held = i - entry_bar
            if close_vals[i] < ma_vals[i] or held >= max_hold_days:
                state = 0
                position[i] = 0
            else:
                position[i] = 1
            continue

        if state == 0:
            if (
                is_pivot_vals[i]
                and not np.isnan(slope_recent_vals[i])
                and not np.isnan(slope_prior_vals[i])
                and above_ma_vals[i]
                and slope_recent_vals[i] > slope_prior_vals[i]
            ):
                pivot_bar = i
                pivot_price = high_vals[i]
                state = 1
            position[i] = 0
            continue

        if state == 1:
            bars_since_pivot = i - pivot_bar
            if bars_since_pivot > pullback_timeout:
                state = 0
                position[i] = 0
                continue
            if low_vals[i] <= ma_vals[i]:
                pullback_bar = i
                if bars_since_pivot <= 3:
                    state = 2
                else:
                    # volume-increasing check over bars since pivot
                    start = max(pivot_bar, i - bars_since_pivot + 1)
                    seg_vol = vol_vals[start : i + 1]
                    seg_vol_avg = vol_avg_vals[start : i + 1]
                    valid = ~np.isnan(seg_vol_avg)
                    if valid.sum() > 0:
                        cnt_above = (seg_vol[valid] > seg_vol_avg[valid]).sum()
                        vol_increasing = cnt_above >= 0.5 * valid.sum()
                    else:
                        vol_increasing = False
                    if vol_increasing:
                        state = 0
                    else:
                        state = 2
            position[i] = 0
            continue

        if state == 2:
            bars_since_pullback = i - pullback_bar
            if bars_since_pullback > confirm_timeout or close_vals[i] > pivot_price * (1 + breakout_cap_pct):
                state = 0
                position[i] = 0
                continue
            first_bar_of_pullback = bars_since_pullback == 0
            higher_close = i > 0 and close_vals[i] > close_vals[i - 1]
            vol_confirms = (
                not np.isnan(vol_avg_vals[i]) and vol_vals[i] > vol_avg_vals[i] * vol_confirm_mult
            )
            if (first_bar_of_pullback or higher_close) and close_vals[i] > ma_vals[i] and vol_confirms:
                state = 3
                entry_bar = i
                position[i] = 1
            else:
                position[i] = 0
            continue

    return pd.Series(position, index=df.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
