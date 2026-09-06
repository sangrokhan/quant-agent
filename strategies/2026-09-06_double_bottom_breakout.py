"""Strategy: Double Bottom chart pattern breakout (W-shaped reversal).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-180):
The double bottom is a classic bullish reversal chart pattern: after a
downtrend, price forms two swing lows at approximately the same price level
(a "W" shape), separated by an intervening swing high (the "neckline"). Per
multiple corroborating sources found this iteration (ThinkMarkets, TrendSpider,
Bajaj AMC, FXIFY, Markets.com), the pattern is CONFIRMED (i.e. the entry
trigger) when price closes above the neckline, ideally on rising volume. This
repo's implementation:

Signal logic
------------
- Detect confirmed swing lows and swing highs via a `swing_window`-bar
  centered rolling-min/max (confirmed causally, consistent with this repo's
  existing swing-detection convention e.g. Elder-Ray divergence strategies).
- A double bottom candidate: two consecutive confirmed swing lows within
  `max_pattern_gap` bars of each other, whose prices differ by no more than
  `low_similarity_pct` (the sources' "similar lows" requirement), with a
  confirmed swing HIGH (the neckline) occurring strictly between them.
- Entry (long): the first close, after the second swing low, that closes
  above the neckline price -- the source's own literal confirmation trigger.
  Optionally require volume on the breakout bar to exceed
  `breakout_vol_mult` times its trailing `vol_ma_window`-day average (the
  sources' "ideally supported by rising volume" caveat, made a strict,
  tunable requirement here to isolate its effect).
- Exit: max_hold_days time-stop, or close falling back below the neckline
  (pattern invalidation -- a standard technical-pattern stop rule).

First chart-pattern-family Double Bottom strategy in this repo. The only
other classic multi-swing chart pattern already tested is Cup-and-Handle
(2026-09-06-172, rejected decisively) -- Double Bottom is a structurally
simpler two-swing-low-plus-neckline pattern, a genuinely distinct
construction (no rounded-correction-then-handle-shakeout requirement).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series {0,1} long/flat
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _confirmed_swing_lows(series: pd.Series, window: int) -> pd.Series:
    roll_min = series.rolling(2 * window + 1, center=True, min_periods=2 * window + 1).min()
    is_low = series == roll_min
    return is_low.shift(window).fillna(False)


def _confirmed_swing_highs(series: pd.Series, window: int) -> pd.Series:
    roll_max = series.rolling(2 * window + 1, center=True, min_periods=2 * window + 1).max()
    is_high = series == roll_max
    return is_high.shift(window).fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    max_pattern_gap: int = 60,
    low_similarity_pct: float = 0.03,
    require_volume_confirmation: bool = False,
    breakout_vol_mult: float = 1.5,
    vol_ma_window: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    high = df["high"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    swing_low = _confirmed_swing_lows(low, swing_window)
    swing_high = _confirmed_swing_highs(high, swing_window)
    vol_ma = volume.rolling(vol_ma_window).mean()

    idx = df.index
    n = len(idx)

    pos = pd.Series(0, index=idx, dtype=int)
    in_pos = False
    entry_idx = None
    neckline = None

    state = "SEEK_LOW1"
    low1_idx = None
    low1_price = None
    neckline_candidate = None
    neckline_idx = None

    for i in range(n):
        lo = low.iloc[i]
        hi = high.iloc[i]
        c = close.iloc[i]

        if in_pos:
            days_held = i - entry_idx
            hit_time = days_held >= max_hold_days
            hit_invalidation = c < neckline
            if hit_time or hit_invalidation:
                in_pos = False
            else:
                pos.iloc[i] = 1
                continue

        if state == "SEEK_LOW1":
            if bool(swing_low.iloc[i]):
                low1_idx, low1_price = i, lo
                state = "SEEK_NECKLINE"
                neckline_candidate, neckline_idx = None, None
        elif state == "SEEK_NECKLINE":
            if i - low1_idx > max_pattern_gap:
                state = "SEEK_LOW1"
            elif bool(swing_high.iloc[i]):
                neckline_candidate, neckline_idx = hi, i
                state = "SEEK_LOW2"
            elif bool(swing_low.iloc[i]) and lo < low1_price:
                # New, lower low before a neckline formed -- reset reference.
                low1_idx, low1_price = i, lo
        elif state == "SEEK_LOW2":
            if i - low1_idx > max_pattern_gap:
                state = "SEEK_LOW1"
            elif bool(swing_low.iloc[i]):
                similar = abs(lo - low1_price) <= low_similarity_pct * low1_price
                if similar:
                    # Double bottom candidate confirmed -- wait for neckline breakout.
                    state = "WAIT_BREAKOUT"
                    neckline = neckline_candidate
                else:
                    # Treat as a new reference low.
                    low1_idx, low1_price = i, lo
                    state = "SEEK_NECKLINE"
                    neckline_candidate, neckline_idx = None, None
        elif state == "WAIT_BREAKOUT":
            if i - low1_idx > max_pattern_gap * 2:
                state = "SEEK_LOW1"
            elif c > neckline:
                vol_ok = True
                if require_volume_confirmation:
                    vol_ok = bool(volume.iloc[i] >= breakout_vol_mult * vol_ma.iloc[i]) if not pd.isna(vol_ma.iloc[i]) else False
                if vol_ok:
                    in_pos = True
                    entry_idx = i
                    pos.iloc[i] = 1
                    state = "SEEK_LOW1"

    return pos


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret
