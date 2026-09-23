"""Strategy: Change of Character (CHoCH) bullish market-structure-shift reversal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-039):
Per multiple corroborating "Smart Money Concepts" sources (the5ers.com's
"Market Structure Explained: BOS, CHoCH & Swing Highs", Daily Price
Action's CHoCH rules, and ICT Trading's "Bullish/Bearish Reversal & CHOCH
vs BOS vs MSS" -- all surfaced via a Google AI-overview synthesis after
`web_search` returned no results for this query; `browser_exec` fallback
used per RESEARCH_LOOP.md Step 2): a bullish Change of Character (CHoCH)
occurs when, during an established downtrend (a sequence of Lower Highs
(LH) and Lower Lows (LL)), price breaks and CLOSES above the most recent
Lower High -- the swing high that produced the last LL -- signaling the
downtrend's internal structure has just shifted and an early reversal is
underway. Sources are explicit that confirmation requires a decisive
candle-body close past the swing high, not merely a wick sweep (distinct
from the repo's existing Swing Failure Pattern / liquidity-sweep entries,
which key off a same-bar wick-and-reject, not a structural close-through-
level of a specific PRIOR SWING HIGH in a downtrend context).

This is the first Change-of-Character / Market-Structure-Shift strategy in
this repo (0 prior KB hits for "Change of Character", "CHoCH", or "Market
Structure Shift") -- distinct from the existing ICT Order Block, Fair
Value Gap, and Swing Failure Pattern entries (all rejected), each of which
uses a different specific mechanical trigger within the broader "Smart
Money Concepts" toolkit.

Signal logic
------------
- Swing highs/lows detected via fractal pivots over a rolling
  `swing_window` (a peak/trough flanked by `swing_window` bars on both
  sides that are lower/higher, per source's "flanked by a minimum of 2
  lower/higher highs/lows" definition).
- Track the current confirmed market-structure state: downtrend
  (sequence of LH/LL) vs uptrend (HH/HL), inferred from the last two
  swing highs and last two swing lows.
- Bullish CHoCH trigger: while in a confirmed downtrend state, close[t]
  closes ABOVE the most recent Lower High level (not just a wick) --
  candle-body confirmation per source.
- Entry (long) on the bullish CHoCH bar.
- Exit: a subsequent bearish CHoCH (close breaks back below the most
  recent swing low established since entry), OR a max_hold_days
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


def _find_swing_points(high: pd.Series, low: pd.Series, swing_window: int):
    roll_max = high.rolling(2 * swing_window + 1, center=True).max()
    roll_min = low.rolling(2 * swing_window + 1, center=True).min()
    swing_high = (high == roll_max) & high.notna()
    swing_low = (low == roll_min) & low.notna()
    return swing_high.fillna(False), swing_low.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    max_hold_days: int = 30,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0, leverage_cap} long/flat position series.

    Detects bullish Change-of-Character (CHoCH) events: while in a
    confirmed downtrend (LH/LL swing sequence), a candle-body close above
    the most recent Lower High signals reversal and triggers a long entry.
    Exit on a subsequent bearish CHoCH (close below the most recent swing
    low since entry) or a max_hold_days time-stop.
    """
    df = _prep(price_df)
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    n = len(close)

    swing_high, swing_low = _find_swing_points(high, low, swing_window)

    # Build ordered lists of confirmed swing highs/lows with their bar index.
    swing_highs = []  # list of (idx, price)
    swing_lows = []
    # For each bar, track the most recent confirmed swing high/low seen so far
    last_swing_high_price = np.full(n, np.nan)
    last_swing_high_idx = np.full(n, -1, dtype=int)
    last_swing_low_price = np.full(n, np.nan)
    last_swing_low_idx = np.full(n, -1, dtype=int)

    cur_sh_price, cur_sh_idx = np.nan, -1
    cur_sl_price, cur_sl_idx = np.nan, -1
    for i in range(n):
        if swing_high.iloc[i]:
            cur_sh_price = high.iloc[i]
            cur_sh_idx = i
        if swing_low.iloc[i]:
            cur_sl_price = low.iloc[i]
            cur_sl_idx = i
        last_swing_high_price[i] = cur_sh_price
        last_swing_high_idx[i] = cur_sh_idx
        last_swing_low_price[i] = cur_sl_price
        last_swing_low_idx[i] = cur_sl_idx

    # Determine downtrend state: prior swing high > current swing high AND
    # prior swing low > current swing low would be a downtrend (LH, LL).
    # We approximate "in a downtrend" as: the last TWO swing highs are
    # decreasing (LH) -- i.e. current confirmed swing high is lower than
    # the swing high before it.
    sh_prices = []
    sh_positions = []
    sl_prices = []
    sl_positions = []
    in_downtrend = np.zeros(n, dtype=bool)
    prev_sh_price, prev_sh_idx = np.nan, -1

    seen_highs = []  # (idx, price)
    for i in range(n):
        if swing_high.iloc[i]:
            seen_highs.append((i, high.iloc[i]))
        # downtrend confirmed if we have >=2 swing highs and the latest < the one before it
        if len(seen_highs) >= 2 and seen_highs[-1][1] < seen_highs[-2][1]:
            in_downtrend[i] = True
        elif len(seen_highs) >= 2:
            in_downtrend[i] = False
        # carry forward the last known state
        if i > 0 and len(seen_highs) < 2:
            in_downtrend[i] = in_downtrend[i - 1] if i > 0 else False

    in_downtrend = pd.Series(in_downtrend, index=close.index).ffill().fillna(False)

    lh_price = pd.Series(last_swing_high_price, index=close.index)
    sl_price = pd.Series(last_swing_low_price, index=close.index)

    bullish_choch = (close > lh_price) & in_downtrend.shift(1).fillna(False)
    # Only fire once per LH level: require prior bar's close <= that LH
    prev_close = close.shift(1)
    bullish_choch = bullish_choch & (prev_close <= lh_price.shift(1))

    position = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    entry_idx = 0
    entry_sl_at_start = None
    for i in range(n):
        if in_position:
            held = i - entry_idx
            current_sl = sl_price.iloc[i]
            bearish_break = (not np.isnan(current_sl)) and close.iloc[i] < current_sl
            if bearish_break or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0.0
                continue
            position.iloc[i] = leverage_cap
        else:
            if bool(bullish_choch.iloc[i]):
                in_position = True
                entry_idx = i
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
