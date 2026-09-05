"""Strategy: Elder's Force Index(39) bullish divergence, confirmed by zero-line cross.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-048):
Per StockCharts ChartSchool's Force Index page (also mirrored verbatim on
MQL5): "A bullish divergence is confirmed when the Force Index (39)
crosses into positive territory." This is a precise, source-stated
mechanical confirmation rule for trading Force Index divergences,
distinct from the already-accepted EFI short/long dual-EMA pullback
strategy in this repo (2026-09-04-049, accepted for QQQ: waits for the
SHORT EFI to dip below zero and cross back up while the LONG EFI stays
positive -- a pullback-in-an-uptrend continuation setup, not a
divergence-at-a-low reversal setup).

Concrete mechanical rule:
- Force Index(1) = (close - close.shift(1)) * volume; Force Index(39) =
  39-period EMA of Force Index(1) (StockCharts' own longer smoothing
  period, specifically associated with the divergence-confirmation rule
  as opposed to the shorter 13-period trend-following smoothing).
- A "swing low" bar is a local minimum of close over a +/-`pivot_window`
  bar window (confirmed `pivot_window` bars later, same construction as
  this repo's other divergence-family strategies, e.g. 2026-09-05-047).
- Bullish divergence: at the current confirmed swing low, close is a
  LOWER low than the prior swing low (within `lookback_bars`), while
  Force Index(39) at the current swing low is a HIGHER low than at the
  prior swing low (selling pressure genuinely waning even as price makes
  a new low).
- Entry (long): once divergence is flagged, wait for FI(39) to cross from
  <=0 to >0 (StockCharts' own stated confirmation trigger) within
  `confirm_window` bars of the divergence being flagged.
- Exit: FI(39) crosses back below zero, close closes below the
  divergence swing-low's close (failed bounce), or a max_hold_days
  time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _force_index(df: pd.DataFrame, span: int) -> pd.Series:
    close, volume = df["close"], df["volume"]
    fi1 = (close - close.shift(1)) * volume
    return fi1.ewm(span=span, adjust=False).mean().fillna(0.0)


def _find_swing_lows(close: pd.Series, pivot_window: int) -> np.ndarray:
    n = len(close)
    c = close.to_numpy()
    idxs = []
    for i in range(pivot_window, n - pivot_window):
        window_slice = c[i - pivot_window : i + pivot_window + 1]
        if c[i] == window_slice.min():
            idxs.append(i)
    return np.array(idxs, dtype=int)


def generate_signals(
    price_df: pd.DataFrame,
    fi_span: int = 39,
    pivot_window: int = 5,
    lookback_bars: int = 60,
    confirm_window: int = 15,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    fi = _force_index(df, fi_span)
    swing_low_idx = _find_swing_lows(close, pivot_window)

    divergence_flagged_at = []  # bar indices (confirm bar of the swing low) where divergence detected
    swing_low_close_by_confirm = {}
    prior_low_idx = None
    for low_i in swing_low_idx:
        confirm_i = low_i + pivot_window
        if confirm_i >= n:
            continue
        if prior_low_idx is not None and (low_i - prior_low_idx) <= lookback_bars:
            price_lower_low = close.iloc[low_i] < close.iloc[prior_low_idx]
            fi_higher_low = fi.iloc[low_i] > fi.iloc[prior_low_idx]
            if price_lower_low and fi_higher_low:
                divergence_flagged_at.append(confirm_i)
                swing_low_close_by_confirm[confirm_i] = close.iloc[low_i]
        prior_low_idx = low_i

    fi_np = fi.to_numpy()
    entry = pd.Series(False, index=close.index)
    entry_swing_low_close = {}
    for flag_i in divergence_flagged_at:
        window_end = min(n, flag_i + confirm_window)
        for j in range(flag_i, window_end):
            if j > 0 and fi_np[j - 1] <= 0 and fi_np[j] > 0:
                entry.iloc[j] = True
                entry_swing_low_close[j] = swing_low_close_by_confirm[flag_i]
                break

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    active_swing_low_close = None
    for i in range(n):
        if in_position:
            held = i - entry_idx
            failed_bounce = active_swing_low_close is not None and close.iloc[i] < active_swing_low_close
            fi_neg = fi.iloc[i] < 0
            if failed_bounce or fi_neg or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                active_swing_low_close = entry_swing_low_close.get(i)
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = position.shift(1).fillna(0) * close.pct_change().fillna(0.0)
    return daily_ret
