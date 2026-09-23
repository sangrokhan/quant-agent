"""Strategy: ICT Optimal Trade Entry (OTE) — 62%-79% Fibonacci retracement zone.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-043):
Per multiple corroborating "Inner Circle Trader" (ICT) sources
(chartinglens.com's "ICT OTE Explained", theinnercircletraders.com's "OTE
in Trading", completetradersedge.com's "Optimal Trade Entry (OTE): The ICT
Precision Entry Guide" -- all surfaced via a Google AI-overview synthesis
after `web_search` returned no results; `browser_exec` fallback used per
RESEARCH_LOOP.md Step 2): after a strong impulsive "displacement" move
(defined here as a swing from a confirmed swing low to a confirmed swing
high whose magnitude exceeds a `displacement_atr_mult`x-ATR threshold, a
proxy for the source's qualitative "strong impulsive candle(s)"
requirement), price retraces into the 62%-79% Fibonacci retracement band
of that impulse leg -- the "Optimal Trade Entry" (OTE) zone where
institutional order flow is hypothesized to concentrate -- with 70.5%
(midpoint of the 62%-79% band) as the source's stated "sweet spot". Entry
triggers when price first touches/enters the OTE zone (bullish case: a
retracement down into the zone during an up-impulse) while still closing
above the 79% level (invalidation line); stop below the 79% level (or the
swing low, per source); target at the swing high or beyond.

This is the first ICT Optimal Trade Entry strategy in this repo (0 prior
KB hits for "Optimal Trade Entry" or "OTE") -- distinct from the repo's
existing ICT Order Block, Fair Value Gap, CHoCH, and BOS entries (none of
which use this specific Fibonacci-retracement-band-of-a-displacement-move
construction).

Signal logic
------------
- Swing highs/lows via fractal pivots over a rolling `swing_window`.
- Displacement leg: a confirmed swing-low-to-swing-high move (impulse)
  whose (high - low) exceeds `displacement_atr_mult` x ATR(atr_window).
- OTE zone (bullish): [high - 0.79*(high-low), high - 0.62*(high-low)]
  (retracement measured down from the impulse high).
- Entry: after a confirmed displacement leg, within `retest_window` bars,
  price's low first touches into the OTE zone (low <= zone upper bound)
  while closing above the zone's lower (79%) bound (invalidation line).
- Exit: close breaks below the 79% invalidation level, price reaches the
  swing high (take-profit), or a max_hold_days time-stop.

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


def _find_swing_points(high: pd.Series, low: pd.Series, swing_window: int):
    roll_max = high.rolling(2 * swing_window + 1, center=True).max()
    roll_min = low.rolling(2 * swing_window + 1, center=True).min()
    swing_high = (high == roll_max) & high.notna()
    swing_low = (low == roll_min) & low.notna()
    return swing_high.fillna(False), swing_low.fillna(False)


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    displacement_atr_mult: float = 2.0,
    atr_window: int = 14,
    ote_low: float = 0.62,
    ote_high: float = 0.79,
    retest_window: int = 15,
    max_hold_days: int = 30,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0, leverage_cap} long/flat position series."""
    df = _prep(price_df)
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    n = len(close)

    swing_high, swing_low = _find_swing_points(high, low, swing_window)
    atr = _atr(high, low, close, atr_window)

    # Collect ordered swing pivots and, for each swing-low->swing-high pair
    # (in that order), check displacement magnitude.
    pivots = []
    for i in range(n):
        if swing_low.iloc[i]:
            pivots.append((i, "low", float(low.iloc[i])))
        elif swing_high.iloc[i]:
            pivots.append((i, "high", float(high.iloc[i])))
    cleaned = []
    for p in pivots:
        if cleaned and cleaned[-1][1] == p[1]:
            if (p[1] == "low" and p[2] < cleaned[-1][2]) or (p[1] == "high" and p[2] > cleaned[-1][2]):
                cleaned[-1] = p
        else:
            cleaned.append(p)

    active = []  # patterns pending retest: {high_idx, low_price, high_price, expiry}
    pattern_by_high_idx = {}
    for k in range(len(cleaned) - 1):
        l_i, l_t, l_p = cleaned[k]
        h_i, h_t, h_p = cleaned[k + 1]
        if not (l_t == "low" and h_t == "high"):
            continue
        leg = h_p - l_p
        if leg <= 0:
            continue
        atr_at_high = atr.iloc[h_i] if not np.isnan(atr.iloc[h_i]) else None
        if atr_at_high is None or atr_at_high <= 0:
            continue
        if leg < displacement_atr_mult * atr_at_high:
            continue
        zone_upper = h_p - ote_low * leg
        zone_lower = h_p - ote_high * leg
        pattern_by_high_idx.setdefault(h_i, []).append({
            "zone_upper": zone_upper, "zone_lower": zone_lower, "target": h_p,
        })

    position = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    entry_idx = 0
    entry_target = None
    entry_stop = None
    pending = []

    for i in range(n):
        if i in pattern_by_high_idx:
            for pat in pattern_by_high_idx[i]:
                pat["expiry"] = i + retest_window
                pending.append(pat)

        if in_position:
            held = i - entry_idx
            hit_target = close.iloc[i] >= entry_target
            hit_stop = close.iloc[i] < entry_stop
            if hit_target or hit_stop or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0.0
                continue
            position.iloc[i] = leverage_cap
        else:
            triggered = None
            still_pending = []
            for pat in pending:
                if i > pat["expiry"]:
                    continue
                if low.iloc[i] <= pat["zone_upper"] and close.iloc[i] > pat["zone_lower"]:
                    triggered = pat
                    continue
                still_pending.append(pat)
            pending = still_pending
            if triggered is not None:
                in_position = True
                entry_idx = i
                entry_target = triggered["target"]
                entry_stop = triggered["zone_lower"]
                position.iloc[i] = leverage_cap
            else:
                position.iloc[i] = 0.0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
