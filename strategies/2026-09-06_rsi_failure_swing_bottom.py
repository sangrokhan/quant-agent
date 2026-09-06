"""Strategy: RSI Failure Swing Bottom (Wilder's original reversal signal).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-134):
Per J. Welles Wilder's original "New Concepts in Technical Trading
Systems" (as summarized by Elearnmarkets and corroborated by
tradethatswing.com / LuxAlgo / rsimonitor.com): "A failure swing bottom
takes place when the price makes a lower low but RSI fails to make a
lower low and rises above the recent swing high (fail point) of the
indicator, triggering a buy signal ... during the first low RSI goes below
the 30 oversold level while during the second low, the indicator makes a
swing low above the 30 oversold level." Wilder himself: "Failure Swings
above 70 or below 30 are very strong indications of a market reversal."
This is a genuinely distinct RSI-family technique from all previously
tested strategies in this repo (plain RSI(2)/RSI(14) oversold-threshold
crosses, Connors RSI composite, RSI divergence, RSI+volume confirmation,
etc.) since it requires the specific 4-point swing-low/swing-high-break
state-machine pattern, not just a threshold cross or price/RSI slope
divergence.

Signal logic (failure swing BOTTOM only, long-only per SAFETY.md)
------------
1. Find the most recent local RSI swing low (`swing1_low`, at index i1)
   that occurred below `oversold_level` (30 default).
2. Find the RSI's local swing high (`fail_point`, at index i2 > i1)
   between that swing low and the next swing low.
3. Find the next local RSI swing low (`swing2_low`, at index i3 > i2)
   that is ABOVE `oversold_level` (RSI "fails" to make a lower low),
   while price's corresponding close makes a LOWER low than at i1 (the
   required price/RSI divergence pre-condition for a true failure swing,
   per the source's "price makes a lower low but RSI fails to").
4. Entry: long at the close of the bar where RSI subsequently breaks back
   above `fail_point` (the swing high identified in step 2) -- the
   "break of the fail point" confirmation the source requires before
   acting.
5. Exit: max_hold_days time-stop, or RSI crossing back below
   `oversold_level`, whichever comes first.

Local swings are detected via a simple `swing_window`-bar rolling
min/max comparison (a swing low/high is a bar whose RSI value is the
min/max within a `swing_window`-bar centered window) -- kept simple and
causal (using only fully-formed windows, i.e. the swing is only
"confirmed" `swing_window` bars after it occurs, avoiding lookahead).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series {0,1} long/flat
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


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _confirmed_swing_lows(rsi: pd.Series, window: int) -> pd.Series:
    """A bar i (confirmed at i+window) is a swing low if it's the min RSI
    within [i-window, i+window]."""
    roll_min = rsi.rolling(2 * window + 1, center=True, min_periods=2 * window + 1).min()
    is_low = (rsi == roll_min)
    # confirmed `window` bars later (shift forward so index t means "we now know bar t-window was a swing low")
    return is_low.shift(window).fillna(False)


def _confirmed_swing_highs(rsi: pd.Series, window: int) -> pd.Series:
    roll_max = rsi.rolling(2 * window + 1, center=True, min_periods=2 * window + 1).max()
    is_high = (rsi == roll_max)
    return is_high.shift(window).fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    oversold_level: float = 30.0,
    swing_window: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    rsi = _rsi(close, rsi_window)

    swing_low_confirmed = _confirmed_swing_lows(rsi, swing_window)
    swing_high_confirmed = _confirmed_swing_highs(rsi, swing_window)

    idx = df.index
    n = len(idx)

    pos = pd.Series(0, index=idx, dtype=int)
    in_pos = False
    entry_idx = None

    # State for building the failure-swing pattern.
    state = "SEEK_SWING1"  # -> SEEK_FAILPOINT -> SEEK_SWING2 -> WAIT_BREAK
    swing1_idx = None
    swing1_rsi = None
    swing1_close = None
    fail_point_idx = None
    fail_point_rsi = None

    for i in range(n):
        r = rsi.iloc[i]
        c = close.iloc[i]

        # Position management (evaluated first each bar).
        if in_pos:
            days_held = i - entry_idx
            hit_time = days_held >= max_hold_days
            hit_rsi_exit = r < oversold_level
            if hit_time or hit_rsi_exit:
                in_pos = False
            else:
                pos.iloc[i] = 1
                continue

        # Pattern-building state machine (only advances when flat).
        if state == "SEEK_SWING1":
            if bool(swing_low_confirmed.iloc[i]) and r < oversold_level:
                swing1_idx, swing1_rsi, swing1_close = i, r, c
                state = "SEEK_FAILPOINT"
        elif state == "SEEK_FAILPOINT":
            if bool(swing_high_confirmed.iloc[i]):
                fail_point_idx, fail_point_rsi = i, r
                state = "SEEK_SWING2"
            elif bool(swing_low_confirmed.iloc[i]) and r < oversold_level:
                # A fresh lower swing low before finding a fail point -- restart.
                swing1_idx, swing1_rsi, swing1_close = i, r, c
        elif state == "SEEK_SWING2":
            if bool(swing_low_confirmed.iloc[i]):
                if r > oversold_level and c < swing1_close:
                    # Valid failure-swing precondition: price lower low, RSI higher low.
                    state = "WAIT_BREAK"
                else:
                    # Not a valid failure swing -- restart search from this new swing low if oversold.
                    if r < oversold_level:
                        swing1_idx, swing1_rsi, swing1_close = i, r, c
                        state = "SEEK_FAILPOINT"
                    else:
                        state = "SEEK_SWING1"
        elif state == "WAIT_BREAK":
            if fail_point_rsi is not None and r > fail_point_rsi:
                # Confirmation: RSI breaks back above the fail point -> entry.
                in_pos = True
                entry_idx = i
                pos.iloc[i] = 1
                state = "SEEK_SWING1"
                swing1_idx = swing1_rsi = swing1_close = None
                fail_point_idx = fail_point_rsi = None

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    oversold_level: float = 30.0,
    swing_window: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        rsi_window=rsi_window,
        oversold_level=oversold_level,
        swing_window=swing_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret
