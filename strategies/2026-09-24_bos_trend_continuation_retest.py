"""Strategy: Break of Structure (BOS) trend-continuation with pullback retest entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-040):
Per multiple corroborating "Smart Money Concepts" sources (fluxcharts.com's
"Break of Structure (BOS) Explained", Daily Price Action's "SMC Market
Structure: BoS And CHoCH Made Simple", and Evest/SabioTrade/Pineify's BOS
guides -- surfaced via a Google AI-overview synthesis after `web_search`
returned no results; `browser_exec` fallback used per RESEARCH_LOOP.md
Step 2): a bullish Break of Structure (BOS) occurs during an ALREADY
established uptrend (Higher-High/Higher-Low sequence) when price
CANDLE-BODY closes above the most recent Higher High, confirming trend
CONTINUATION (not reversal -- the opposite economic thesis from this
repo's just-tested Change of Character, 2026-09-24-039, which fires during
a downtrend to signal reversal). Sources' own recommended entry sequence
is NOT to chase the breakout bar itself: wait for a pullback/retest of the
just-broken prior high (which becomes new support) before entering long,
reducing the risk of buying an overextended breakout.

This is the first Break-of-Structure strategy in this repo (0 prior KB
hits) -- distinct from CHoCH (2026-09-24-039, reversal signal during a
downtrend, immediate-close entry) and from the repo's existing plain
breakout/Donchian-style strategies (which don't require the specific
prior-HH/HL uptrend-structure precondition or the retest-before-entry
sequencing).

Signal logic
------------
- Swing highs/lows via fractal pivots over a rolling `swing_window` (same
  detection mechanism as 2026-09-24_choch_market_structure_shift.py).
- Confirmed uptrend state: the last two swing highs are increasing (HH)
  AND the last two swing lows are increasing (HL).
- BOS event: while in a confirmed uptrend, close crosses (candle-body)
  above the most recent swing high for the first time since that high was
  set.
- After a BOS event, arm a "pullback watch" for `retest_window` bars:
  enter long on the first bar where price pulls back to touch/cross into
  the broken level (low <= broken_high_level * (1 + retest_tolerance))
  while still closing above it (confirming the level now holds as
  support, per source's "role reversal" rule).
- Exit: close breaks back below the most recent swing low since entry
  (structure invalidated), or a max_hold_days time-stop.

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


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    retest_window: int = 10,
    retest_tolerance: float = 0.01,
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

    # Track last two confirmed swing highs / lows for HH/HL detection, and
    # the most recent swing low overall (for the exit rule).
    seen_highs = []  # (idx, price)
    seen_lows = []
    uptrend = np.zeros(n, dtype=bool)
    last_sh_price = np.full(n, np.nan)
    last_sl_price = np.full(n, np.nan)
    cur_sh, cur_sl = np.nan, np.nan

    for i in range(n):
        if swing_high.iloc[i]:
            seen_highs.append((i, float(high.iloc[i])))
            cur_sh = float(high.iloc[i])
        if swing_low.iloc[i]:
            seen_lows.append((i, float(low.iloc[i])))
            cur_sl = float(low.iloc[i])
        last_sh_price[i] = cur_sh
        last_sl_price[i] = cur_sl

        hh = len(seen_highs) >= 2 and seen_highs[-1][1] > seen_highs[-2][1]
        hl = len(seen_lows) >= 2 and seen_lows[-1][1] > seen_lows[-2][1]
        uptrend[i] = hh and hl

    uptrend_s = pd.Series(uptrend, index=close.index)
    last_sh_s = pd.Series(last_sh_price, index=close.index)
    last_sl_s = pd.Series(last_sl_price, index=close.index)

    prev_close = close.shift(1)
    bos_event = (
        uptrend_s.shift(1).fillna(False)
        & (close > last_sh_s)
        & (prev_close <= last_sh_s.shift(1))
    )

    position = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    entry_idx = 0
    armed_level = None
    armed_until = -1

    for i in range(n):
        if in_position:
            held = i - entry_idx
            current_sl = last_sl_s.iloc[i]
            broken = (not np.isnan(current_sl)) and close.iloc[i] < current_sl
            if broken or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0.0
                continue
            position.iloc[i] = leverage_cap
        else:
            # Arm a new pullback watch on a fresh BOS event
            if bool(bos_event.iloc[i]):
                armed_level = float(last_sh_s.iloc[i])
                armed_until = i + retest_window

            triggered = False
            if armed_level is not None and i <= armed_until:
                tol_level = armed_level * (1 + retest_tolerance)
                if low.iloc[i] <= tol_level and close.iloc[i] > armed_level:
                    triggered = True

            if triggered:
                in_position = True
                entry_idx = i
                armed_level = None
                position.iloc[i] = leverage_cap
            else:
                if armed_level is not None and i > armed_until:
                    armed_level = None
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
