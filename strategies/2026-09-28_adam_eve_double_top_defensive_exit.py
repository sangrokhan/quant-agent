"""Strategy: SMA trend-following long with a Bulkowski Adam & Eve Double
Top defensive exit overlay.

Hypothesis (source: https://thepatternsite.com/aedt.html, Thomas
Bulkowski, read 2026-09-28 via browser_exec):

Adam & Eve Double Top: twin peaks that LOOK DIFFERENT from each other
(Adam = narrow, pointed, spike-like; Eve = wider, rounded), price
variation between peaks < 3%, valley drop between them >= 10%,
confirming when price closes below the valley floor. Source's own stats:
average decline 16%, break-even failure rate 21%. Distinct from this
repo's already-tested Double Top Setup and 'Big M' deep-drop double top
strategies -- this variant specifically requires the TWO PEAKS TO LOOK
DIFFERENT (measured here via a bar-count/width proxy: the Adam peak
spans fewer bars near its high than the Eve peak) rather than just
"twin peaks at similar price," which is what makes it a distinct
Bulkowski sub-classification from plain/generic double tops.

Since this repo is long-only, operationalized as a DEFENSIVE EXIT
overlay on a plain SMA-crossover trend-following long (matching this
repo's convention for bearish reversal patterns -- UTAD, Pipe Top):
a confirmed Adam & Eve Double Top while long triggers an immediate exit.

Mechanical proxy (daily-bar, long-only):
- Baseline entry: close crosses above SMA(trend_window).
- Detect two swing-high peaks (via rolling-window fractal pivots) within
  a trailing lookback window, peak prices within `peak_tolerance_pct` of
  each other, separated by `min_valley_drop_pct` between the peaks'
  intervening low.
- "Looks different" proxy: the first peak (Adam) must have a narrower
  width (fewer bars where high is within adam_width_tolerance of the
  peak) than the second peak (Eve), consistent with Adam being a sharp
  spike and Eve being a rounded top.
- Confirmation: first bar whose close falls below the valley low between
  the two peaks.
- Exit: baseline SMA trend-filter break, OR a confirmed Adam & Eve
  Double Top while long (defensive exit), OR a max_hold_days time-stop.

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _find_pivots(series: pd.Series, window: int) -> pd.Series:
    n = len(series)
    pivots = pd.Series(0, index=series.index, dtype=int)
    half = window // 2
    vals = series.values
    for i in range(half, n - half):
        window_vals = vals[i - half: i + half + 1]
        if vals[i] == window_vals.max() and (window_vals == vals[i]).sum() == 1:
            pivots.iloc[i] = 1
        elif vals[i] == window_vals.min() and (window_vals == vals[i]).sum() == 1:
            pivots.iloc[i] = -1
    return pivots


def _peak_width(high: np.ndarray, peak_idx: int, tolerance_pct: float, span: int = 10) -> int:
    """Count bars around peak_idx (within +/- span) whose high is within
    tolerance_pct of the peak high -- a proxy for peak sharpness/width."""
    peak_high = high[peak_idx]
    n = len(high)
    count = 0
    for j in range(max(0, peak_idx - span), min(n, peak_idx + span + 1)):
        if peak_high > 0 and abs(high[j] - peak_high) / peak_high <= tolerance_pct:
            count += 1
    return count


def _adam_eve_confirmed(
    df: pd.DataFrame,
    pivot_window: int,
    lookback: int,
    peak_tolerance_pct: float,
    min_valley_drop_pct: float,
    adam_width_max: int,
    eve_width_min: int,
) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    high_pivots = _find_pivots(high, pivot_window)

    high_arr = high.to_numpy()
    low_arr = low.to_numpy()
    close_arr = close.to_numpy()
    n = len(df)

    peak_idx_list = [i for i in range(n) if high_pivots.iloc[i] == 1]

    confirmed = np.zeros(n, dtype=bool)

    for k in range(1, len(peak_idx_list)):
        eve_idx = peak_idx_list[k]
        adam_idx = peak_idx_list[k - 1]
        if eve_idx - adam_idx < 5 or eve_idx - adam_idx > lookback:
            continue
        adam_price = high_arr[adam_idx]
        eve_price = high_arr[eve_idx]
        if adam_price <= 0:
            continue
        if abs(adam_price - eve_price) / adam_price > peak_tolerance_pct:
            continue

        valley_low = low_arr[adam_idx:eve_idx + 1].min()
        valley_drop = (adam_price - valley_low) / adam_price
        if valley_drop < min_valley_drop_pct:
            continue

        adam_w = _peak_width(high_arr, adam_idx, 0.01)
        eve_w = _peak_width(high_arr, eve_idx, 0.01)
        if not (adam_w <= adam_width_max and eve_w >= eve_width_min):
            continue

        for j in range(eve_idx, min(eve_idx + lookback, n)):
            if close_arr[j] < valley_low:
                confirmed[j] = True
                break

    return pd.Series(confirmed, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    pivot_window: int = 7,
    peak_tolerance_pct: float = 0.03,
    min_valley_drop_pct: float = 0.06,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    sma = close.rolling(trend_window).mean()
    trend_ok = close > sma
    fresh_entry = trend_ok & (~trend_ok.shift(1).fillna(False))

    ae_top = _adam_eve_confirmed(
        df,
        pivot_window=pivot_window,
        lookback=35,
        peak_tolerance_pct=peak_tolerance_pct,
        min_valley_drop_pct=min_valley_drop_pct,
        adam_width_max=3,
        eve_width_min=1,
    )

    n = len(df)
    trend_ok_arr = trend_ok.to_numpy()
    fresh_entry_arr = fresh_entry.to_numpy()
    ae_top_arr = ae_top.to_numpy()

    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = (
                not bool(trend_ok_arr[i])
                or bool(ae_top_arr[i])
                or hold_count >= max_hold_days
            )
            if exit_now:
                in_pos = False
                hold_count = 0
            else:
                pos.iloc[i] = 1.0
        if not in_pos and bool(fresh_entry_arr[i]):
            in_pos = True
            hold_count = 0
            pos.iloc[i] = 1.0

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    pivot_window: int = 7,
    peak_tolerance_pct: float = 0.03,
    min_valley_drop_pct: float = 0.06,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        trend_window=trend_window,
        pivot_window=pivot_window,
        peak_tolerance_pct=peak_tolerance_pct,
        min_valley_drop_pct=min_valley_drop_pct,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret
