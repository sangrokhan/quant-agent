"""Strategy: Elder-Ray Bull Power bullish divergence.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-135):
Per Capital.com's Elder-Ray Index explainer: "Bearish divergence: forms
when price makes a higher high, but bull power makes a lower high. This
may suggest that buying pressure is fading, even though price is still
rising." This strategy tests the mirror-image BULLISH divergence: price
makes a LOWER low while Bull Power (High - EMA13, Dr. Alexander Elder)
makes a HIGHER low over the same swing -- buying pressure quietly
strengthening even as price nominally makes a new low, historically a
leading indicator of reversal. This is distinct from the two Elder-Ray
strategies already tested in this repo (2026-09-04-037 and
2026-09-04-110, both of which use a simple "Bear Power negative-but-rising"
threshold condition, NOT a genuine price-vs-indicator divergence pattern
requiring two comparable swing points).

Signal logic
------------
- 13-period EMA (Elder's "consensus of value").
- Bull Power = High - EMA13.
- Detect price swing lows via a `swing_window`-bar centered rolling-min
  (confirmed causally, i.e. only known `swing_window` bars after the
  swing occurs).
- Bullish divergence: at the second of two consecutive confirmed price
  swing lows (within `max_swing_gap` bars of each other), price's low is
  LOWER than the prior swing low's price, but Bull Power's value at the
  second swing low is HIGHER than Bull Power's value at the first swing
  low.
- Entry: long at the close of the bar where Bull Power subsequently
  crosses back above 0 (confirmation that buying pressure has actually
  turned positive, not just "less negative").
- Exit: max_hold_days time-stop, or Bull Power crossing back below 0.

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
    is_low = (series == roll_min)
    return is_low.shift(window).fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 13,
    swing_window: int = 5,
    max_swing_gap: int = 40,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    ema = close.ewm(span=ema_window, min_periods=ema_window, adjust=False).mean()
    bull_power = high - ema

    price_swing_low = _confirmed_swing_lows(low, swing_window)

    idx = df.index
    n = len(idx)

    pos = pd.Series(0, index=idx, dtype=int)
    in_pos = False
    entry_idx = None

    state = "SEEK_SWING1"
    swing1_idx = None
    swing1_low = None
    swing1_bp = None
    divergence_confirmed_idx = None  # index at which divergence itself was detected

    for i in range(n):
        bp = bull_power.iloc[i]
        lo = low.iloc[i]

        if in_pos:
            days_held = i - entry_idx
            hit_time = days_held >= max_hold_days
            hit_bp_exit = bp < 0
            if hit_time or hit_bp_exit:
                in_pos = False
            else:
                pos.iloc[i] = 1
                continue

        if state == "SEEK_SWING1":
            if bool(price_swing_low.iloc[i]):
                swing1_idx, swing1_low, swing1_bp = i, lo, bp
                state = "SEEK_SWING2"
        elif state == "SEEK_SWING2":
            if i - swing1_idx > max_swing_gap:
                # Too much time passed -- restart from this bar if it's a swing low.
                if bool(price_swing_low.iloc[i]):
                    swing1_idx, swing1_low, swing1_bp = i, lo, bp
                else:
                    state = "SEEK_SWING1"
            elif bool(price_swing_low.iloc[i]):
                if lo < swing1_low and bp > swing1_bp:
                    # Bullish divergence confirmed.
                    divergence_confirmed_idx = i
                    state = "WAIT_BP_CROSS"
                else:
                    # Not a valid divergence -- treat this as the new reference swing.
                    swing1_idx, swing1_low, swing1_bp = i, lo, bp
        elif state == "WAIT_BP_CROSS":
            if bp > 0:
                in_pos = True
                entry_idx = i
                pos.iloc[i] = 1
                state = "SEEK_SWING1"
                swing1_idx = swing1_low = swing1_bp = None
                divergence_confirmed_idx = None
            elif i - divergence_confirmed_idx > max_swing_gap:
                # Divergence stale, give up and restart.
                state = "SEEK_SWING1"
                swing1_idx = swing1_low = swing1_bp = None
                divergence_confirmed_idx = None

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    ema_window: int = 13,
    swing_window: int = 5,
    max_swing_gap: int = 40,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        ema_window=ema_window,
        swing_window=swing_window,
        max_swing_gap=max_swing_gap,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret
