"""Strategy: Simple Equal-Lows (EQL) liquidity-zone bounce (long only) --
direct simplification of this same cron trigger's near-miss/rejected
compound construction (2026-09-24-051, EQL+sweep+strong-body+fresh-FVG).

Hypothesis (knowledge_base id TBD, this cron trigger):
Direct follow-up to this trigger's own iteration 8 (2026-09-24-051), whose
own notes explicitly flagged: "The equal-lows/equal-highs concept itself
(0 prior hits) may be worth revisiting in a future iteration with a
SIMPLER construction (e.g. plain EQL-zone bounce without the FVG/strong-
body compound filter) since the compound filter here may be
over-restricting an otherwise viable liquidity-zone concept." This
iteration tests exactly that: drop the ATR-scaled strong-body-breakout
requirement AND the fresh-FVG confirmation requirement, keeping only the
core EQL zone identification (two pivot lows within a tight equality
threshold) and a plain bounce entry (price dips to/below the zone then
closes back above it within a short confirmation window) -- the minimal
form of the concept per LuxAlgo's own stated primary use-case ("as
support/resistance levels for mean reversion").

Signal logic (long side only)
------------------------------
- EQL zone identification: identical to 2026-09-24-051 (two confirmed
  pivot lows within max_eql_distance_bars of each other, price difference
  <= equality_threshold_pct).
- Entry: a later bar's low touches/dips below the EQL zone AND, within
  confirm_bars, a bar closes back above the zone (no strong-body or FVG
  requirement -- the simplified "plain bounce").
- Exit: max_hold_days time-stop, or close falling back below the EQL zone
  (invalidation).
- Optional close>SMA(trend_window) uptrend gate (default True).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


def _confirmed_pivot_lows(df: pd.DataFrame, pivot_window: int) -> pd.Series:
    low = df["low"]
    window = 2 * pivot_window + 1
    rolling_min = low.rolling(window, center=True).min()
    is_pivot_low_raw = (low == rolling_min)
    return is_pivot_low_raw.shift(pivot_window).fillna(False).astype(bool)


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 5,
    max_eql_distance_bars: int = 40,
    equality_threshold_pct: float = 0.02,
    confirm_bars: int = 3,
    max_hold_days: int = 15,
    trend_window: int = 200,
    trend_filter: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    n = len(df)

    is_pivot_low = _confirmed_pivot_lows(df, pivot_window)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False) if trend_filter else pd.Series(True, index=close.index)

    pivot_low_indices = [j for j in range(n) if bool(is_pivot_low.iloc[j])]

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    eql_level = None

    i = pivot_window
    while i < n:
        if in_position:
            held = i - entry_idx
            invalidated = eql_level is not None and close.iloc[i] < eql_level
            if invalidated or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                i += 1
                continue
            position.iloc[i] = 1
            i += 1
            continue

        recent_lows = [j for j in pivot_low_indices if j < i]
        found_zone = None
        if len(recent_lows) >= 2:
            p2 = recent_lows[-1]
            for p1 in reversed(recent_lows[:-1]):
                if p2 - p1 > max_eql_distance_bars:
                    break
                price1, price2 = low.iloc[p1], low.iloc[p2]
                if price2 == 0:
                    continue
                if abs(price1 - price2) / price2 <= equality_threshold_pct:
                    found_zone = (price1 + price2) / 2.0
                    break

        if found_zone is not None and bool(uptrend.iloc[i]) and low.iloc[i] <= found_zone:
            confirmed_at = None
            for j in range(i, min(i + confirm_bars + 1, n)):
                if close.iloc[j] > found_zone:
                    confirmed_at = j
                    break
            if confirmed_at is not None:
                in_position = True
                entry_idx = confirmed_at
                eql_level = found_zone
                i = confirmed_at
                position.iloc[i] = 1
                i += 1
                continue

        position.iloc[i] = 0
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
