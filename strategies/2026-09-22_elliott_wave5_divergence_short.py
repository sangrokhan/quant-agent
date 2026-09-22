"""Strategy: Elliott Wave 5 momentum divergence -- short at exhausted top.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Source: https://algobars.com/strategy-templates/elliott/elliott-wave-5-divergence/
(accessed 2026-09-22, browser_exec after web_extract ddgs-backend refused
extraction). Wave 5 of an Elliott impulse often terminates with momentum
divergence: price makes a new extreme (above the Wave 3 peak) while RSI/
MACD show weaker readings than at the Wave 3 peak (bearish divergence,
"trend exhaustion"). Source's explicit rule: identify Wave 3 (the
strongest-momentum peak in a 1-2-3-4 structure), then when price later
exceeds that peak (entering "Wave 5 territory") with RSI(14) LOWER than at
the Wave 3 peak AND a lower MACD-histogram peak, confirmed by a bearish
reversal candle, enter short. Target: the Wave 4 low first, then Wave 1
territory.

First Elliott Wave-5-divergence strategy in this repo (0 prior KB hits for
"Wave 5 Divergence") -- distinct from this cron trigger's own Wave 3
breakout (2026-09-22-095, long entry on impulse continuation) and ABC
Correction (2026-09-22-096, long entry at corrective completion): this is
the only SHORT-side Elliott strategy tested, trading the exhaustion of the
impulse itself via a genuine price/momentum divergence rather than a
Fibonacci-ratio wave-structure rule.

Signal logic (daily bars)
--------------------------
- Swing pivots via the same rolling `pivot_window`-bar local-extremum test
  used by this repo's other Elliott/harmonic-family strategies.
- Wave 3 peak = a confirmed swing high preceded by at least one prior lower
  swing high (approximating "Wave 3 is the strongest-momentum peak" without
  needing a full formal 1-2-3-4 count -- the most recent swing high that
  itself followed an earlier, lower swing high).
- RSI(14) and MACD histogram computed on close.
- Wave 5 divergence: a LATER swing high (price) exceeds the Wave-3-peak
  price level, but RSI at that later high is lower than RSI at the Wave 3
  peak by at least `rsi_div_min` points, AND the MACD histogram value at
  the later high is lower than at the Wave 3 peak (source's "weaker
  readings than wave 3").
- Entry (short, i.e. exit-to-flat from a would-be long / represented here
  as a negative position since this repo trades long/short via a signed
  position series): on the bar where the divergence is confirmed AND that
  bar (or the next bar) is a bearish reversal candle (close < open).
- Exit: close falls to/below the Wave 4 low (the most recent swing low
  before the Wave-5 peak, source's stated first target), OR close rises
  back above the Wave 5 peak (stop, source: "above the wave 5 extreme
  high"), OR a `max_hold_days` time-stop.

Position convention: generate_signals returns {-1, 0} (short/flat) rather
than {0, 1}, consistent with this repo's existing short-side strategies
(e.g. strategies/2026-09-08_wyckoff_upthrust_distribution_short.py).
generate_returns computes returns from that signed position, so a
short position profits when price falls.
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


def _find_pivots(high: pd.Series, low: pd.Series, window: int):
    n = len(high)
    high_arr = high.to_numpy()
    low_arr = low.to_numpy()
    is_swing_high = np.zeros(n, dtype=bool)
    is_swing_low = np.zeros(n, dtype=bool)
    for i in range(window, n - window):
        seg_high = high_arr[i - window : i + window + 1]
        seg_low = low_arr[i - window : i + window + 1]
        if high_arr[i] == seg_high.max():
            is_swing_high[i] = True
        if low_arr[i] == seg_low.min():
            is_swing_low[i] = True
    return is_swing_high, is_swing_low


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd_hist(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line - signal_line


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 5,
    rsi_div_min: float = 5.0,
    max_hold_days: int = 30,
) -> pd.Series:
    df = _prep(price_df)
    high, low, close, open_ = df["high"], df["low"], df["close"], df["open"]

    is_swing_high, is_swing_low = _find_pivots(high, low, pivot_window)
    rsi = _rsi(close)
    macd_hist = _macd_hist(close)

    n = len(df)
    high_arr = high.to_numpy()
    low_arr = low.to_numpy()
    close_arr = close.to_numpy()
    open_arr = open_.to_numpy()
    rsi_arr = rsi.to_numpy()
    macd_arr = macd_hist.to_numpy()

    pos_arr = [0] * n
    in_pos = False
    hold_days = 0
    entry_stop = None
    entry_target = None

    swing_highs_seen = []  # list of (idx, price, rsi_val, macd_val)
    last_swing_low_val = None
    wave3_peak = None  # (idx, price, rsi_val, macd_val)

    for i in range(n):
        if in_pos:
            hold_days += 1
            hit_target = (entry_target is not None) and close_arr[i] <= entry_target
            hit_stop = (entry_stop is not None) and close_arr[i] > entry_stop
            if hit_target or hit_stop or hold_days >= max_hold_days:
                in_pos = False
                pos_arr[i] = 0
                hold_days = 0
            else:
                pos_arr[i] = -1
            continue

        if is_swing_low[i]:
            last_swing_low_val = low_arr[i]

        if is_swing_high[i]:
            cur = (i, high_arr[i], rsi_arr[i], macd_arr[i])
            if swing_highs_seen and cur[1] > swing_highs_seen[-1][1]:
                # A higher swing high following a lower one -- candidate
                # "Wave 3" (strongest momentum peak in the sequence so far).
                wave3_peak = swing_highs_seen[-1] if wave3_peak is None or swing_highs_seen[-1][1] > wave3_peak[1] else wave3_peak
                # Actually treat the NEW higher high as a candidate Wave 5
                # if we already have a wave3_peak below it.
                if wave3_peak is not None and cur[1] > wave3_peak[1] and not np.isnan(cur[2]) and not np.isnan(wave3_peak[2]):
                    rsi_diverges = (wave3_peak[2] - cur[2]) >= rsi_div_min
                    macd_diverges = cur[3] < wave3_peak[3]
                    if rsi_diverges and macd_diverges:
                        # Wave 5 divergence detected at bar i; look for a
                        # bearish confirmation candle at this bar or check
                        # entry on this bar if it's already bearish.
                        if close_arr[i] < open_arr[i]:
                            in_pos = True
                            hold_days = 0
                            entry_stop = high_arr[i]
                            entry_target = last_swing_low_val if last_swing_low_val is not None else close_arr[i] * 0.95
                            pos_arr[i] = -1
                            wave3_peak = None
                            swing_highs_seen = []
                            continue
                # Update wave3_peak to be the most recent confirmed peak
                # for the next potential Wave 5 comparison.
                wave3_peak = swing_highs_seen[-1] if swing_highs_seen else wave3_peak
            swing_highs_seen.append(cur)
            if len(swing_highs_seen) > 5:
                swing_highs_seen.pop(0)

        pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    pivot_window: int = 5,
    rsi_div_min: float = 5.0,
    max_hold_days: int = 30,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        pivot_window=pivot_window,
        rsi_div_min=rsi_div_min,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    # Short position: profits when price falls, so multiply by -1 * ret
    # for the -1 position, i.e. position (already signed) * daily_ret
    # gives the correct sign (position=-1 and ret negative -> positive pnl).
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
