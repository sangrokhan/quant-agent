"""Strategy: Donchian channel breakout gated by a statistical volume Z-score
confirmation (not a simple volume ratio), per QuanterLab's "Volume
Confirmation in Breakouts" article
(https://quanterlab.com/articles/breakout-volume-confirmation, read via
browser_exec this iteration -- web_search returned only a 404'd direct URL,
so the article path was found via a Google SERP search and browser_exec
navigation, then the site's internal article-list links).

Hypothesis
----------
A breakout level is where many resting stop-loss and breakout-buy orders
cluster; when a genuine breakout occurs those orders execute together,
producing an above-average volume spike. Per the source: "breakouts on
volume in the top quartile of the recent rolling distribution have hit
rates 10-20 percentage points higher than breakouts on average or
below-average volume," and it explicitly proposes a Volume Z-Score
formalization: Z = (today's volume - rolling mean) / rolling std, with
Z > 2.0 flagging "statistically unusual" volume that "adapts when overall
trading activity is rising or falling" -- distinct from a fixed RVOL ratio
threshold (which this repo already tested at id 2026-09-04-166) because the
Z-score standardizes by the *dispersion* of recent volume, not just its
level, so it should behave differently across changing-volume-regime
periods (e.g. it re-calibrates faster after a low-volume summer lull than
a level ratio would). This repo has tested RVOL-ratio (2026-09-04-166),
OBV-breakout (2026-09-05-060), volume-multiple+candle-quality
(2026-09-10-123), VROC (2026-09-12-140), ATR-filter (2026-09-11-032), and
Livermore-pivotal-point+volume-ratio (2026-09-12-168) gates on Donchian-style
breakouts -- all of them near-missed (Sharpe in the 0.6-1.0 range) but none
used a genuine statistical Z-score of volume. This is that missing variant.

Signal logic
------------
- Donchian upper channel = rolling max of close over `channel_window` days
  (computed on prior bars only, i.e. shifted by 1, to avoid using today's
  own close to define today's breakout level).
- Volume Z-score = (volume - rolling_mean(volume, vol_window)) /
  rolling_std(volume, vol_window), computed over the trailing `vol_window`
  days (also using only prior bars, shifted by 1, for the mean/std to avoid
  incorporating today's own volume into its own baseline).
- Entry (long): close breaks above the prior `channel_window`-day high AND
  the volume Z-score on that same bar >= `z_threshold`.
- Exit: close breaks below the prior `channel_window`-day low (Donchian
  lower-channel breakdown), OR a max holding period of `max_hold_days`
  trading days is reached.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    channel_window: int = 20,
    vol_window: int = 20,
    z_threshold: float = 2.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    # Prior-bar Donchian channel (shifted 1 so today's own bar isn't used
    # to define today's breakout level).
    upper_channel = close.rolling(channel_window).max().shift(1)
    lower_channel = close.rolling(channel_window).min().shift(1)

    # Prior-bar volume Z-score baseline (shifted 1 so today's own volume
    # isn't used to compute its own mean/std).
    vol_mean = volume.rolling(vol_window).mean().shift(1)
    vol_std = volume.rolling(vol_window).std().shift(1)
    vol_z = (volume - vol_mean) / vol_std.replace(0, pd.NA)

    entry = (close > upper_channel) & (vol_z >= z_threshold)
    exit_breakdown = close < lower_channel

    entry = entry.fillna(False)
    exit_breakdown = exit_breakdown.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_breakdown.iloc[i]) or held >= max_hold_days:
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
