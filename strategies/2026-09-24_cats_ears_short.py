"""Strategy: Cat's Ears chart pattern (Siligardos 2012, bearish continuation SHORT).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/CatsEars.html (Thomas Bulkowski's
summary of Giorgos E. Siligardos, Technical Analysis of Stocks &
Commodities, December 2012, browser_exec fallback -- web_search's DDGS
backend cannot extract this domain). Source's own disclosed identification
rules (note: Bulkowski himself has NOT tested this pattern -- "I have not
tested the chart pattern, so I do not offer any performance results" --
this repo tests it independently since none of Bulkowski's own performance
stats exist for it):

    "In essence, the chart pattern is a double top in a downward price
    trend... 1) severe decline, 2) pause (horizontal), 3) left ear forms,
    4) scalp (pause between the two ears), 5) right ear forms, 6) scalp
    line break: the lowest price in the pattern... When price closes
    below the pattern's low, it confirms the pattern as valid... RSI: The
    14-period relative strength index (RSI) during the pattern remains
    below 65... Duration: The length of the cat's ears is between 10 days
    and 2 months (60 days)."

First "Cat's Ears" strategy in this repo (0 prior index hits) -- distinct
from every prior double-top pattern via its required prior SEVERE DECLINE
precondition (a bearish continuation setup, not a reversal-from-uptrend
double top) and its RSI<65 filter throughout formation, tested here as a
SHORT position (simulated in the returns series via position=-1, exactly
like this cron trigger's earlier 2B Top and Busted H&S Bottom short
strategies -- consistent with SAFETY.md's simulation-only scope, no real
order-placement code).

Signal logic (numeric proxy for the source's qualitative 6-phase Cat's
Ears shape)
------------------------------------------------------------------------
1. Swing pivot detection: same rolling-window fractal test used elsewhere
   in this repo to find alternating swing highs (ears)/lows (scalp) over
   `pivot_window`.
2. Severe decline precondition: close at the start of the pattern-search
   window is at least `decline_pct` below its own value `decline_lookback`
   bars earlier (numeric proxy for "the stock to make a severe decline").
3. For each Left-Ear(peak1)-Scalp(valley)-Right-Ear(peak2) swing triple
   within `max_duration_days` of each other (source: duration 10-60
   days), with the severe-decline precondition satisfied before peak1:
   - RSI(14) filter: RSI must stay below `rsi_max` (default 65) at every
     bar from peak1 through peak2 (source's own disclosed filter).
   - scalp_line = the valley's low (lowest price in the pattern).
4. Entry (SHORT): the first bar after peak2 where close closes below the
   scalp_line (source's own "confirms as valid" breakout-down rule).
5. Exit: source's own Measure Rule (height = peak-to-scalp height,
   subtracted from scalp_line to get target C, per source: "Take the
   height of the pattern from highest peak (A) to lowest valley (B) and
   subtract it from the value of the lowest valley (B) to get the target
   C"), OR close recovers back above the higher of the two ears
   (stop-loss, thesis falsified), OR a max_hold_days time-stop, whichever
   comes first.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({-1,0} position series;
        -1 = short, 0 = flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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


def _find_pivots(series: pd.Series, window: int) -> pd.Series:
    n = len(series)
    pivots = pd.Series(0, index=series.index, dtype=int)
    half = window // 2
    vals = series.values
    for i in range(half, n - half):
        window_vals = vals[i - half: i + half + 1]
        if vals[i] == window_vals.max() and (window_vals == vals[i]).sum() == 1:
            pivots.iloc[i] = 1
        elif vals[i] == window_vals.min() and (window_vals == vals[i]).sum() == 1:
            pivots.iloc[i] = -1
    return pivots


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 7,
    decline_lookback: int = 30,
    decline_pct: float = 0.08,
    max_duration_days: int = 60,
    rsi_max: float = 65.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {-1,0} short/flat position series for Cat's Ears completions."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]
    close_arr = close.to_numpy()
    high_arr = high.to_numpy()
    low_arr = low.to_numpy()
    n = len(close_arr)

    rsi = _rsi(close).to_numpy()
    high_pivots = _find_pivots(high, pivot_window)
    low_pivots = _find_pivots(low, pivot_window)

    swing_idx = []
    for i in range(n):
        if high_pivots.iloc[i] == 1:
            swing_idx.append((i, "H", float(high.iloc[i])))
        if low_pivots.iloc[i] == -1:
            swing_idx.append((i, "L", float(low.iloc[i])))
    swing_idx.sort(key=lambda x: x[0])

    alt_swings = []
    for s in swing_idx:
        if alt_swings and alt_swings[-1][1] == s[1]:
            if s[1] == "H" and s[2] > alt_swings[-1][2]:
                alt_swings[-1] = s
            elif s[1] == "L" and s[2] < alt_swings[-1][2]:
                alt_swings[-1] = s
        else:
            alt_swings.append(s)

    entries = {}
    for k in range(len(alt_swings) - 2):
        p1, sc, p2 = alt_swings[k], alt_swings[k + 1], alt_swings[k + 2]
        if not (p1[1] == "H" and sc[1] == "L" and p2[1] == "H"):
            continue
        p1_idx, scalp_idx, p2_idx = p1[0], sc[0], p2[0]
        if p2_idx - p1_idx > max_duration_days:
            continue

        # severe decline precondition: check before p1
        lookback_idx = p1_idx - decline_lookback
        if lookback_idx < 0:
            continue
        prior_price = close_arr[lookback_idx]
        if prior_price <= 0:
            continue
        decline = (prior_price - close_arr[p1_idx]) / prior_price
        if decline < decline_pct:
            continue

        # RSI filter: must stay below rsi_max from p1 through p2
        segment_rsi = rsi[p1_idx: p2_idx + 1]
        if len(segment_rsi) == 0 or np.nanmax(segment_rsi) >= rsi_max:
            continue

        scalp_line = low_arr[scalp_idx]
        higher_ear = max(high_arr[p1_idx], high_arr[p2_idx])
        pattern_top = higher_ear
        height = pattern_top - scalp_line
        if height <= 0:
            continue
        target_price = scalp_line - height

        for j in range(p2_idx + 1, n):
            if close_arr[j] < scalp_line:
                if j not in entries:
                    entries[j] = (target_price, higher_ear)
                break

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_idx = -1
    target_price = -np.inf
    stop_price = np.inf

    for t in range(n):
        if not in_pos and t in entries:
            in_pos = True
            entry_idx = t
            target_price, stop_price = entries[t]
        if in_pos:
            position[t] = -1
            held = t - entry_idx
            hit_target = close_arr[t] <= target_price
            hit_stop = close_arr[t] > stop_price
            if hit_target or hit_stop or held >= max_hold_days:
                in_pos = False

    return pd.Series(position, index=close.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    Position is -1 while short; multiplying by daily returns means a
    price DROP while short (position=-1) produces a POSITIVE strategy
    return, matching a real short position's payoff.
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
