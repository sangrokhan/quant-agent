"""Strategy: Bulkowski Pipe Bottom twin-spike reversal breakout (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/pipeb.html (Thomas Bulkowski's
"Encyclopedia of Chart Patterns" stats page; read via browser_exec after
web_search's DDGS backend returned unrelated/garbage results this
iteration). Source's own disclosed statistics and identification rules:

    "Pipe Bottom: Important Bull Market Results: Break even failure rate:
    8%. Average rise: 54%. Percentage meeting price target: 77%. ...
    Weekly chart: Pipes appear on the daily scale but the ones on the
    weekly charts perform better... Price trend: Usually downward leading
    to the pattern. Shape: Twin and adjacent downward spikes... Overlap:
    The 2 weeks often have a large price overlap but need not bottom at
    the same price. The bottom price variation is 1%... Downtrends: The
    best performing pipes appear at the end of downtrends. Confirmation:
    The pattern confirms (becomes a valid pattern) when price closes
    above the highest high in the pattern. ... Buy: Buy when price closes
    above the higher of the two spikes. ... Stop: If price closes below
    the lower of the two spikes, then close out your position."

Source explicitly notes this pattern performs better on the WEEKLY scale
than the daily scale used throughout this repo (a disclosed caveat, not
hidden) -- tested here on daily bars anyway per this repo's existing
convention (all prior strategies use daily OHLCV via data/loaders.py), but
flagged as a known scale mismatch that may suppress performance relative
to Bulkowski's own weekly-scale statistics. First Pipe Bottom entry in
this repo (0 prior index hits) -- distinct from every prior pattern
tested: it requires exactly two ADJACENT sharp-decline bars with closely
overlapping lows (a twin-spike signature), not a multi-bar consolidation
or a 3+ swing-point structure.

Signal logic (numeric proxy for the source's twin-spike rule)
----------------------------------------------------------------------
1. Spike detection: a bar is a "spike" if its (high-low) range exceeds
   `spike_atr_mult` times the trailing ATR(14) (a large, obvious downward
   thrust, per source's "should stand-alone and be obvious") AND its
   close is in the lower `spike_close_pct` fraction of its own bar range
   (close near the low, consistent with a downward spike).
2. Twin-pipe candidate: two ADJACENT spike bars (i-1, i) whose lows are
   within `low_overlap_pct` of each other (source's disclosed 1%
   tolerance, widened as a tunable parameter since daily-bar noise may
   need more slack than weekly).
3. Downtrend context: close at the start of the pipe is below its own
   SMA(trend_lookback) (source: "usually downward leading to the
   pattern").
4. Confirmation/entry: long the first subsequent bar whose close exceeds
   the higher of the two spike highs (source's own "Buy when price closes
   above the higher of the two spikes").
5. Exit: source's own stop rule (close falls below the lower of the two
   spikes) OR the Measure Rule target (height = higher_spike_high -
   lower_spike_low, target = higher_spike_high + height * target_pct,
   using the source's own disclosed 77% "percentage meeting price
   target") OR a max_hold_days time-stop, whichever comes first.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
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


def _atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    spike_atr_mult: float = 1.5,
    spike_close_pct: float = 0.35,
    low_overlap_pct: float = 0.03,
    trend_lookback: int = 30,
    target_pct: float = 0.77,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    atr = _atr(df, 14)

    bar_range = (high - low).replace(0.0, np.nan)
    close_position_in_range = (close - low) / bar_range  # 0 = at low, 1 = at high
    is_spike = ((high - low) > spike_atr_mult * atr) & (close_position_in_range <= spike_close_pct)

    sma_trend = close.rolling(trend_lookback).mean()
    downtrend = close < sma_trend

    n = len(close)
    high_arr = high.to_numpy()
    low_arr = low.to_numpy()
    close_arr = close.to_numpy()
    is_spike_arr = is_spike.fillna(False).to_numpy()
    downtrend_arr = downtrend.fillna(False).to_numpy()

    raw_confirm = np.zeros(n, dtype=bool)
    upper_spikes = np.full(n, np.nan)
    lower_spikes = np.full(n, np.nan)

    for i in range(1, n):
        if not (is_spike_arr[i - 1] and is_spike_arr[i]):
            continue
        low_prev, low_cur = low_arr[i - 1], low_arr[i]
        if low_prev == 0:
            continue
        overlap_ok = abs(low_cur - low_prev) / low_prev <= low_overlap_pct
        if not overlap_ok:
            continue
        if not downtrend_arr[i]:
            continue
        higher_spike_high = max(high_arr[i - 1], high_arr[i])
        lower_spike_low = min(low_arr[i - 1], low_arr[i])
        # search forward for confirmation close > higher_spike_high
        for t in range(i + 1, min(n, i + 1 + max_hold_days)):
            if close_arr[t] < lower_spike_low:
                break  # invalidated before confirming
            if close_arr[t] > higher_spike_high:
                raw_confirm[t] = True
                upper_spikes[t] = higher_spike_high
                lower_spikes[t] = lower_spike_low
                break

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_bar = -1
    entry_upper = np.nan
    entry_lower = np.nan
    target_price = np.nan

    for t in range(n):
        if raw_confirm[t] and not in_pos:
            in_pos = True
            entry_bar = t
            entry_upper = upper_spikes[t]
            entry_lower = lower_spikes[t]
            height = entry_upper - entry_lower
            target_price = entry_upper + height * target_pct if height > 0 else np.inf
        if in_pos:
            position[t] = 1
            held = t - entry_bar
            failed = close_arr[t] < entry_lower
            hit_target = close_arr[t] >= target_price
            if failed or hit_target or held >= max_hold_days:
                in_pos = False

    return pd.Series(position, index=close.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
