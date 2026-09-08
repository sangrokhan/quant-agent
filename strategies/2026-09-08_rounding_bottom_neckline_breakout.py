"""Strategy: Rounding Bottom (saucer) reversal neckline breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-131):
Per https://www.tradingsim.com/blog/rounding-bottom (TradingSim's Step-by-
Step Guide), a rounding bottom is a U-shaped reversal: a decline slows,
flattens into a range, then gradually turns up in a roughly symmetric
"saucer" shape. The source's own mechanical rules: (1) draw a "neckline"
across the top of the bearish and bullish sides of the pattern (approximated
here as the rolling window's own high), (2) breakout entry when close
penetrates the neckline, (3) stop-loss at the pattern's MIDPOINT (source's
own stated rule, distinct from a stop at the pattern low), (4) target =
neckline + pattern height (neckline-to-trough distance) projected up from
breakout ("the move higher will be at least the size of the rounding bottom
formation").

This is DISTINCT from the only prior saucer-family strategy in this repo
(Cup-and-Handle, 2026-09-06-172), which REQUIRES a post-recovery "handle"
pullback on contracting volume before the breakout entry -- the source's own
point is that a rounding bottom has NO handle, just a direct neckline
breakout after the U-shape completes. It is also distinct from Double Bottom
(2-trough W, 2026-09-08-101) and Inverse Head & Shoulders (3-trough,
2026-09-08-109) since a rounding bottom is a single continuous smooth curve,
not a discrete multi-trough structure -- operationalized here via a
quadratic (parabola) least-squares fit to the window's closes: a good-fit
(R^2 >= min_r2) POSITIVE-curvature (a > 0, i.e. U-shaped, not inverted-U)
fit confirms the rounding-bottom shape, replacing subjective "eyeballing"
with a concrete numeric test.

Signal logic
------------
- Rolling `pattern_window`-day window (default 40). Fit close ~ a*x^2+b*x+c
  via OLS on x=0..window-1. Confirm a rounding bottom when a > 0 (U-shape)
  AND the fit's R^2 >= `min_r2` (default 0.5, a "good enough" fit per the
  source's own visual-symmetry criterion).
- Neckline = max(high) over the confirmed window (source: "a line across the
  top of the bearish and bullish sides").
- Pattern low = min(close) over the window; pattern height = neckline -
  pattern low; midpoint = (neckline + pattern low) / 2 (source's stated
  stop-loss level).
- Entry (long): on a bar where a rounding bottom is freshly confirmed (or
  was confirmed within `breakout_lookback` bars) AND close crosses from
  at/below neckline to strictly above it (the breakout).
- Exit: close falls back below the pattern's own midpoint (stop-loss, per
  source's explicit rule), close reaches the target (neckline + pattern
  height), or a `max_hold_days` time-stop, whichever comes first.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
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


def _fit_quadratic(y: np.ndarray) -> tuple[float, float]:
    """Fit y ~ a*x^2 + b*x + c via OLS; return (a, r_squared)."""
    n = len(y)
    x = np.arange(n, dtype=float)
    X = np.column_stack([x ** 2, x, np.ones(n)])
    coeffs, residuals, rank, sv = np.linalg.lstsq(X, y, rcond=None)
    a = coeffs[0]
    y_pred = X @ coeffs
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    return float(a), float(r2)


def generate_signals(
    price_df: pd.DataFrame,
    pattern_window: int = 40,
    min_r2: float = 0.5,
    breakout_lookback: int = 10,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    n = len(df)

    # Precompute, for each bar i (window ending at i), whether a rounding
    # bottom is confirmed, plus the neckline/midpoint/target for that window.
    confirmed = np.zeros(n, dtype=bool)
    neckline = np.full(n, np.nan)
    midpoint = np.full(n, np.nan)
    target = np.full(n, np.nan)

    close_vals = close.values
    high_vals = high.values

    for i in range(pattern_window - 1, n):
        window_close = close_vals[i - pattern_window + 1 : i + 1]
        a, r2 = _fit_quadratic(window_close)
        if a > 0 and r2 >= min_r2:
            window_high = high_vals[i - pattern_window + 1 : i + 1]
            nk = float(np.max(window_high))
            low_pt = float(np.min(window_close))
            confirmed[i] = True
            neckline[i] = nk
            midpoint[i] = (nk + low_pt) / 2.0
            target[i] = nk + (nk - low_pt)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = None
    target_price = None

    i = pattern_window
    while i < n:
        if in_position:
            held = i - entry_idx
            price_now = close_vals[i]
            if price_now <= stop_price or price_now >= target_price or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                i += 1
                continue
            position.iloc[i] = 1
            i += 1
            continue

        # Look for a recently-confirmed pattern within breakout_lookback bars.
        recent_start = max(pattern_window - 1, i - breakout_lookback)
        found_entry = False
        for j in range(recent_start, i + 1):
            if not confirmed[j]:
                continue
            nk = neckline[j]
            if np.isnan(nk):
                continue
            prior_close = close_vals[i - 1] if i > 0 else close_vals[i]
            if prior_close <= nk and close_vals[i] > nk:
                stop_price = midpoint[j]
                target_price = target[j]
                if stop_price < close_vals[i]:  # sane risk (stop below entry)
                    in_position = True
                    entry_idx = i
                    position.iloc[i] = 1
                    found_entry = True
                break
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
