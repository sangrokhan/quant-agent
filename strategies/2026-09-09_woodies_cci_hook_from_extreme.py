"""Strategy: Woodie's CCI Hook From Extreme (HFE) reversal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-061):
Per MarketBulls' Woodies CCI guide (https://market-bulls.com/woodies-cci/,
browser_exec fallback -- web_search DDGS errored/returned no results for
the direct query), the "Hook From Extreme" (HFE) pattern is "a reversal
signal that occurs when the CCI hooks within the extreme area after a
prolonged trend" -- i.e. CCI spikes below an extreme oversold threshold
(<=-100) then curls/turns back upward WITHOUT necessarily crossing the zero
line, distinct from the already-tested Zero-Line-Reject (2026-09-05-007,
CCI bounces off zero near the centerline) and Trendline Break
(2026-09-06-160, OLS trendline break near zero) patterns which both operate
NEAR zero. HFE specifically operates in the EXTREME zone, treating an
extreme CCI reading followed by a directional curl as an actionable
reversal-from-exhaustion signal -- a genuinely different mechanic within
the same Woodie's CCI indicator family already covered twice in this repo.

Signal logic
------------
- CCI(14) via standard formula: (typical_price - SMA(typical_price, n)) /
  (0.015 * mean_abs_deviation(typical_price, n)).
- Extreme condition: CCI dips to/below extreme_threshold (-100 default)
  within the last hook_lookback bars.
- Hook confirmation: CCI turns up for hook_confirm_bars consecutive bars
  (CCI[t] > CCI[t-1] > ... ) after having touched the extreme, while still
  below the zero line (source's own "within the extreme area" framing).
- Entry (long): hook confirmed.
- Exit: CCI crosses back above the exit_level (e.g. 0, source's zero-line
  framing for taking profit once the reversal completes), or a
  max_hold_days time-stop.
- Flat (no position) whenever not in an active long.

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5/6):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
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


def _cci(df: pd.DataFrame, window: int = 14) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    sma = tp.rolling(window).mean()
    mad = tp.rolling(window).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    cci = (tp - sma) / (0.015 * mad.replace(0, np.nan))
    return cci


def generate_signals(
    price_df: pd.DataFrame,
    cci_window: int = 14,
    extreme_threshold: float = -100.0,
    hook_lookback: int = 5,
    hook_confirm_bars: int = 2,
    exit_level: float = 0.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    cci = _cci(df, window=cci_window)

    touched_extreme = (cci <= extreme_threshold).rolling(hook_lookback, min_periods=1).max().astype(bool)

    rising = cci.diff() > 0
    rising_streak = rising.groupby((~rising).cumsum()).cumsum()
    hook_confirmed = rising_streak >= hook_confirm_bars

    below_zero = cci < 0
    entry = touched_extreme.shift(1).fillna(False) & hook_confirmed & below_zero

    entry_arr = entry.to_numpy()
    cci_arr = cci.to_numpy()
    pos_arr = np.zeros(len(df), dtype=int)

    in_pos = False
    entry_idx = -1
    for i in range(len(df)):
        if in_pos:
            held = i - entry_idx
            if (not np.isnan(cci_arr[i]) and cci_arr[i] >= exit_level) or held >= max_hold_days:
                in_pos = False
            else:
                pos_arr[i] = 1
        if not in_pos and entry_arr[i]:
            in_pos = True
            entry_idx = i
            pos_arr[i] = 1

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    cci_window: int = 14,
    extreme_threshold: float = -100.0,
    hook_lookback: int = 5,
    hook_confirm_bars: int = 2,
    exit_level: float = 0.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        cci_window=cci_window,
        extreme_threshold=extreme_threshold,
        hook_lookback=hook_lookback,
        hook_confirm_bars=hook_confirm_bars,
        exit_level=exit_level,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change()
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns = strat_returns.fillna(0.0)
    return strat_returns
