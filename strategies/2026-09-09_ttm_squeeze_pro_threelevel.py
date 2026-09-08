"""Strategy: TTM Squeeze Pro three-level compression breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-059):
John Carter's Squeeze Pro (per Simpler Trading's own explainer,
https://www.simplertrading.com/tutorials/squeeze-pro, browser_exec fallback
-- web_search DDGS errored with a TLS connection error for the direct
query) extends the classic single-level TTM Squeeze (already tested twice
in this repo: 2026-09-04-091 and 2026-09-08-004, both rejected) into THREE
progressively tighter Bollinger-Bands-inside-Keltner-Channels compression
levels (low/black, mid/red, high/orange, using narrower KC ATR multipliers
for higher compression). Per the source's own claim, "any compression
squeeze is considered fired at the first green dot" (BB expanding back
outside that level's KC), and requiring a HIGHER-compression squeeze before
firing is a higher-conviction filter that "catches moves the [single-level]
squeeze wouldn't have caught." This strategy tests that specific claim: only
take breakout entries when the squeeze recently reached at least a
min_squeeze_level (mid or high) compression before releasing, rather than
firing on any (including the loosest/low) compression level.

Signal logic
------------
- Bollinger Bands: 20-period SMA basis +/- 2 std.
- Keltner Channels at 3 multiplier levels (tighter multiplier = higher
  compression required): kc_mult_low=2.0, kc_mult_mid=1.5, kc_mult_high=1.0
  (all on a 20-EMA basis +/- multiplier*ATR(20)).
- squeeze_level[t] in {0,1,2,3}: 3 if BB fully inside KC(high-mult), else 2
  if inside KC(mid-mult), else 1 if inside KC(low-mult), else 0 (no squeeze).
- "Fired" = squeeze_level drops from >=1 to a lower level (release), and the
  max squeeze_level reached during the preceding lookback_window bars was
  >= min_squeeze_level (the higher-conviction filter under test).
- Momentum direction: linreg-style proxy = close - average(rolling
  Donchian midpoint(20), EMA(20)) (source's standard momentum-histogram
  proxy, reused from 2026-09-04-091's implementation for consistency).
- Entry (long): fired AND momentum > 0.
- Exit: momentum turns <= 0, or a max_hold_days time-stop.
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def _squeeze_level(
    df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    kc_window: int = 20,
    kc_mult_low: float = 2.0,
    kc_mult_mid: float = 1.5,
    kc_mult_high: float = 1.0,
) -> pd.Series:
    close = df["close"]
    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    bb_upper = sma + bb_std * std
    bb_lower = sma - bb_std * std

    ema = close.ewm(span=kc_window, adjust=False).mean()
    atr = _atr(df, kc_window)

    kc_upper_low = ema + kc_mult_low * atr
    kc_lower_low = ema - kc_mult_low * atr
    kc_upper_mid = ema + kc_mult_mid * atr
    kc_lower_mid = ema - kc_mult_mid * atr
    kc_upper_high = ema + kc_mult_high * atr
    kc_lower_high = ema - kc_mult_high * atr

    inside_low = (bb_upper < kc_upper_low) & (bb_lower > kc_lower_low)
    inside_mid = (bb_upper < kc_upper_mid) & (bb_lower > kc_lower_mid)
    inside_high = (bb_upper < kc_upper_high) & (bb_lower > kc_lower_high)

    level = pd.Series(0, index=df.index, dtype=int)
    level[inside_low] = 1
    level[inside_mid] = 2
    level[inside_high] = 3
    return level


def _momentum(df: pd.DataFrame, window: int = 20) -> pd.Series:
    donchian_mid = (df["high"].rolling(window).max() + df["low"].rolling(window).min()) / 2
    ema = df["close"].ewm(span=window, adjust=False).mean()
    avg_ref = (donchian_mid + ema) / 2
    return df["close"] - avg_ref


def generate_signals(
    price_df: pd.DataFrame,
    min_squeeze_level: int = 2,
    lookback_window: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    level = _squeeze_level(df)
    momentum = _momentum(df)

    max_level_recent = level.rolling(lookback_window, min_periods=1).max().shift(1)
    released = (level < level.shift(1)) & (level.shift(1) >= 1)
    fired = released & (max_level_recent >= min_squeeze_level)
    bullish = momentum > 0

    entry = fired & bullish

    entry_arr = entry.to_numpy()
    momentum_arr = momentum.to_numpy()
    pos_arr = np.zeros(len(df), dtype=int)

    in_pos = False
    entry_idx = -1
    for i in range(len(df)):
        if in_pos:
            held = i - entry_idx
            if momentum_arr[i] <= 0 or held >= max_hold_days:
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
    min_squeeze_level: int = 2,
    lookback_window: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        min_squeeze_level=min_squeeze_level,
        lookback_window=lookback_window,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change()
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns = strat_returns.fillna(0.0)
    return strat_returns
