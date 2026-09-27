"""Strategy: Post-Parabolic-Phase pullback long (adapted from LuxAlgo's
Parabolic Phase concept, for daily-bar signals without swing-pivot trendlines).

Hypothesis (source: https://www.luxalgo.com/library/indicator/parabolic-phase/,
read 2026-09-28 via browser_exec while browsing LuxAlgo's indicator library
for a fresh angle -- PZO/Correlation Trend Indicator/Elder SafeZone/many
smart-money-concept indicators already saturated in this repo per
strategies_index.jsonl novelty checks this iteration):

LuxAlgo's "Parabolic Phase" indicator is a rules-based detector for a
trend's terminal accelerating stage: it requires 3 consecutive impulse legs
each steepening by a 1.2x slope-ratio factor, contracting pullbacks, AND a
long-term stretch extreme (price at/above the 95th percentile of its
distance from a 200-period SMA over the trailing 500 bars). Source's own
trading guidance: once confirmed, "the job shifts from judging trend health
to managing the exit" -- the phase ends on either a trendline break or a
pullback deeper than any seen inside the phase, after which "a dotted level
marks the midpoint of the accelerated move as a reference for the give-back
that often follows" (the 50% retracement).

This repo's daily-OHLCV-only strategies (see data/loaders.py) can't
replicate LuxAlgo's swing-pivot-based trendline construction exactly, so we
adapt the concept into fully mechanical proxies:
  - "Stretch extreme": today's (close - SMA200)/SMA200 is at/above its own
    trailing 500-day `stretch_percentile`-th percentile (matches source's
    disclosed 95th-percentile-of-500-bar-history default exactly).
  - "3 accelerating impulse legs" proxy: 5-day ROC has grown by at least
    `acceleration_factor` (default 1.2, matching source's own default)
    across each of the last 2 non-overlapping 5-day windows (i.e.
    ROC5[t] >= accel*ROC5[t-5] >= accel^2*ROC5[t-10] and all three positive
    -- an accelerating, positive-momentum sequence).
  - "Trendline break" proxy: close crosses below EMA(10) (a short,
    responsive moving average standing in for the source's per-leg
    trendline, since we lack swing-pivot geometry on daily bars alone).

Trade logic (long-only, buying the post-blowoff PULLBACK, not fading the
top directly, since this repo's SAFETY.md scope is long-only): once a
Parabolic Phase is confirmed (stretch extreme + accelerating legs) AND then
ends (EMA(10) break), enter long at that break's close, betting on the
source's own stated "give-back" dynamic reversing into at least a partial
bounce toward the 50% retracement of the accelerated move; exit at that
50%-retracement target, a stop below the phase's own lowest close since
the stretch extreme was first flagged, or a max_hold_days time-stop.

First "Parabolic Phase" strategy in this repo (0 prior hits; distinct from
the many already-tested Parabolic SAR entries, which is explicitly a
DIFFERENT indicator per the source's own FAQ "Is this the same as the
Parabolic SAR?").

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _compute_signals(
    df: pd.DataFrame,
    stretch_window: int,
    stretch_percentile: float,
    acceleration_factor: float,
    trendline_ema: int,
    max_hold_days: int,
    reward_r_multiple: float = 1.0,
):
    close = df["close"]
    sma200 = close.rolling(200).mean()
    dist_pct = (close - sma200) / sma200

    stretch_thresh = dist_pct.rolling(stretch_window).quantile(stretch_percentile / 100.0)
    stretched = dist_pct >= stretch_thresh

    roc5 = close.pct_change(5)
    accel_ok = (
        (roc5 > 0)
        & (roc5.shift(5) > 0)
        & (roc5.shift(10) > 0)
        & (roc5 >= acceleration_factor * roc5.shift(5))
        & (roc5.shift(5) >= acceleration_factor * roc5.shift(10))
    )

    phase_confirmed = stretched & accel_ok

    ema = close.ewm(span=trendline_ema, adjust=False).mean()
    trendline_break = close < ema

    n = len(df)
    close_arr = close.to_numpy()
    phase_confirmed_arr = phase_confirmed.to_numpy()
    trendline_break_arr = trendline_break.to_numpy()
    sma200_arr = sma200.to_numpy()

    trades = []
    i = 0
    phase_active = False
    phase_start_idx = None
    phase_high = -np.inf

    while i < n:
        if not phase_active:
            if phase_confirmed_arr[i]:
                phase_active = True
                phase_start_idx = i
                phase_high = close_arr[i]
            i += 1
            continue

        # phase active: track high, watch for the trendline break (phase end)
        phase_high = max(phase_high, close_arr[i])
        if trendline_break_arr[i]:
            # Phase ends here -> entry at this bar's close.
            entry_idx = i
            entry_price = close_arr[i]
            phase_low = min(close_arr[phase_start_idx : i + 1])
            stop_price = phase_low
            risk = entry_price - stop_price
            target_price = entry_price + reward_r_multiple * risk

            if risk > 0:
                exit_idx = None
                exit_price = None
                low = df["low"].to_numpy()
                high = df["high"].to_numpy()
                for k in range(entry_idx + 1, min(entry_idx + 1 + max_hold_days, n)):
                    if low[k] <= stop_price:
                        exit_idx = k
                        exit_price = stop_price
                        break
                    if high[k] >= target_price:
                        exit_idx = k
                        exit_price = target_price
                        break
                if exit_idx is None:
                    exit_idx = min(entry_idx + max_hold_days, n - 1)
                    exit_price = close_arr[exit_idx]
                trades.append((entry_idx, exit_idx, entry_price, exit_price))
                i = exit_idx + 1
                phase_active = False
                phase_high = -np.inf
                continue
            phase_active = False
            phase_high = -np.inf
        i += 1

    return trades


def generate_signals(
    price_df: pd.DataFrame,
    stretch_window: int = 500,
    stretch_percentile: float = 95.0,
    acceleration_factor: float = 1.2,
    trendline_ema: int = 10,
    max_hold_days: int = 10,
    reward_r_multiple: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    trades = _compute_signals(
        df, stretch_window, stretch_percentile, acceleration_factor, trendline_ema, max_hold_days,
        reward_r_multiple,
    )
    pos = pd.Series(0.0, index=df.index)
    for entry_idx, exit_idx, _, _ in trades:
        pos.iloc[entry_idx : exit_idx + 1] = 1.0
    return pos


def generate_returns(
    price_df: pd.DataFrame,
    stretch_window: int = 500,
    stretch_percentile: float = 95.0,
    acceleration_factor: float = 1.2,
    trendline_ema: int = 10,
    max_hold_days: int = 10,
    reward_r_multiple: float = 1.0,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    trades = _compute_signals(
        df, stretch_window, stretch_percentile, acceleration_factor, trendline_ema, max_hold_days,
        reward_r_multiple,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = pd.Series(0.0, index=df.index)

    for entry_idx, exit_idx, entry_price, exit_price in trades:
        if exit_idx > entry_idx:
            strat_ret.iloc[entry_idx + 1 : exit_idx + 1] = daily_ret.iloc[
                entry_idx + 1 : exit_idx + 1
            ]
        exit_close = df["close"].iloc[exit_idx]
        if exit_close != 0 and exit_price != exit_close:
            prior_close = df["close"].iloc[exit_idx - 1] if exit_idx > 0 else df["close"].iloc[exit_idx]
            if prior_close != 0:
                strat_ret.iloc[exit_idx] = (exit_price / prior_close) - 1.0

    return strat_ret
