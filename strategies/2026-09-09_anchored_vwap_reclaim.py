"""Strategy: Anchored VWAP reclaim (breakout-anchored, pullback entry).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-102):
Per daytradingtoolkit.com's "Anchored VWAP Trend Strategy for Day
Traders" (Brian Shannon's anchored-VWAP concept): anchoring a VWAP
calculation to a genuinely significant pivot (a confirmed breakout, a
swing high/low, an earnings gap) rather than resetting daily produces a
multi-day/week volume-weighted average that acts as dynamic
support/resistance for the cohort of participants who entered at that
specific event. Source's exact setup: entry trigger = price returns to
touch the anchored VWAP line on declining volume, followed by a
confirmation candle closing back on the anchor's favorable side on
rising volume; stop = beyond the anchored VWAP line or the confirmation
candle's low, whichever is further; target = prior swing high since the
anchor (>= 2:1 reward:risk).

Operationalized on daily bars: the anchor re-sets whenever price makes a
new `anchor_window`-day high (a "confirmed breakout" proxy). From that
anchor bar forward, an anchored VWAP is computed as the cumulative
volume-weighted average price since the anchor. Entry: close pulls back
to within `touch_tolerance` of the anchored VWAP on below-average volume
(vs. `vol_window`-day average), followed within `confirm_window` bars by
a close back above the anchored VWAP on above-average volume. Exit: stop
below the anchored VWAP value at entry (or a max_hold_days time-stop),
target = the anchor-window rolling high since the anchor.

First Anchored VWAP (event-anchored cumulative VWAP as dynamic S/R)
strategy in this repo (0 prior hits on "VWAP Anchored"/"Anchored VWAP")
-- distinct from the existing Session VWAP strategy (resets daily, no
multi-day anchoring) and from Volume Profile POC/VAH (rolling-window
histogram, not a cumulative running average from a single anchor event).

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
    anchor_window: int = 60,
    touch_tolerance: float = 0.01,
    vol_window: int = 20,
    confirm_window: int = 3,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    n = len(close)

    rolling_high = close.rolling(anchor_window).max()
    is_new_high = (close == rolling_high).fillna(False)

    avg_volume = volume.rolling(vol_window).mean()

    anchored_vwap = pd.Series(index=close.index, dtype=float)
    anchor_high_target = pd.Series(index=close.index, dtype=float)
    anchor_idx = None
    cum_pv = 0.0
    cum_vol = 0.0

    for i in range(n):
        if bool(is_new_high.iloc[i]):
            anchor_idx = i
            cum_pv = 0.0
            cum_vol = 0.0
        if anchor_idx is not None:
            cum_pv += typical_price.iloc[i] * volume.iloc[i]
            cum_vol += volume.iloc[i]
            anchored_vwap.iloc[i] = cum_pv / cum_vol if cum_vol > 0 else float("nan")
            anchor_high_target.iloc[i] = close.iloc[max(anchor_idx, i - anchor_window + 1) : i + 1].max()
        else:
            anchored_vwap.iloc[i] = float("nan")
            anchor_high_target.iloc[i] = float("nan")

    below_avg_vol = volume < avg_volume
    above_avg_vol = volume > avg_volume
    touch = (close >= anchored_vwap * (1 - touch_tolerance)) & (close <= anchored_vwap * (1 + touch_tolerance))
    touch_on_low_vol = touch & below_avg_vol.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = None
    target_price = None
    pending_touch_idx = None

    for i in range(n):
        if in_position:
            held = i - entry_idx
            stop_hit = stop_price is not None and close.iloc[i] < stop_price
            target_hit = target_price is not None and close.iloc[i] >= target_price
            if stop_hit or target_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                stop_price = None
                target_price = None
                continue
            position.iloc[i] = 1
        else:
            if bool(touch_on_low_vol.iloc[i]):
                pending_touch_idx = i
            if pending_touch_idx is not None and i - pending_touch_idx <= confirm_window:
                vwap_val = anchored_vwap.iloc[i]
                if (
                    vwap_val == vwap_val
                    and close.iloc[i] > vwap_val
                    and bool(above_avg_vol.iloc[i])
                    and i > pending_touch_idx
                ):
                    in_position = True
                    entry_idx = i
                    stop_price = vwap_val
                    target_price = anchor_high_target.iloc[i]
                    pending_touch_idx = None
                    position.iloc[i] = 1
                    continue
            if pending_touch_idx is not None and i - pending_touch_idx > confirm_window:
                pending_touch_idx = None
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
