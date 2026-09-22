"""Strategy: Al Brooks Three-Push Wedge Reversal (short at wedge top,
RSI divergence).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Source: https://algobars.com/strategy-templates/al-brooks/brooks-wedge-reversal/
(accessed 2026-09-22, browser_exec after web_extract ddgs-backend refused
extraction). A "three-push wedge": three consecutive higher-highs (each
with a SMALLER gain than the previous, forming a narrowing/weakening
sequence), ideally confirmed by bearish RSI divergence (RSI lower on the
3rd push than the 1st push) -- signals trend exhaustion. Short entry on a
bearish reversal candle at the 3rd push high, stop above the 3rd push
extreme, target the wedge base.

Distinct from this repo's existing Falling/Rising Wedge chart-pattern
strategies (2026-09-08-113, 2026-09-09-097 -- both trade BREAKOUTS out of
a converging-trendline consolidation, a continuation/reversal-of-range
pattern) via requiring the specific THREE-PUSH counting structure with
DIMINISHING gains per push plus RSI divergence, which is a trend-exhaustion
reversal pattern at the end of an active trend, not a range-breakout
pattern.

Signal logic (daily bars)
--------------------------
- Swing pivots via the same rolling `pivot_window`-bar local-extremum test
  used by this repo's other price-action/Elliott/harmonic strategies.
- Track the last 3 confirmed swing highs (H1, H2, H3, chronological order).
  Valid three-push structure requires:
    - H1 < H2 < H3 (three consecutive higher highs)
    - (H2 - H1) > (H3 - H2) (each push has a SMALLER gain than the
      previous -- diminishing momentum, source's "narrowing wedge")
    - RSI(14) at H3 < RSI(14) at H1 (bearish divergence, source's "RSI
      lower on 3rd push than 1st")
- Entry (short): on the bar of H3 (or shortly after) with a bearish
  reversal candle (close < open).
- Exit: close falls to/below the most recent swing low before H1 (the
  "wedge base" target), OR close rises back above H3 (stop, source's
  "above the 3rd push extreme"), OR a `max_hold_days` time-stop.

Position convention: generate_signals returns {-1, 0} (short/flat),
consistent with this repo's other short-side strategies (e.g. this cron
trigger's own 2026-09-22_elliott_wave5_divergence_short.py).
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


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 4,
    max_hold_days: int = 25,
) -> pd.Series:
    df = _prep(price_df)
    high, low, close, open_ = df["high"], df["low"], df["close"], df["open"]

    is_swing_high, is_swing_low = _find_pivots(high, low, pivot_window)
    rsi = _rsi(close)

    n = len(df)
    high_arr = high.to_numpy()
    low_arr = low.to_numpy()
    close_arr = close.to_numpy()
    open_arr = open_.to_numpy()
    rsi_arr = rsi.to_numpy()

    pos_arr = [0] * n
    in_pos = False
    hold_days = 0
    entry_stop = None
    entry_target = None

    swing_highs = []  # list of (idx, price, rsi_val)
    last_swing_low_before_h1 = None
    swing_lows_seen = []

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
            swing_lows_seen.append((i, low_arr[i]))
            if len(swing_lows_seen) > 5:
                swing_lows_seen.pop(0)

        if is_swing_high[i]:
            swing_highs.append((i, high_arr[i], rsi_arr[i]))
            if len(swing_highs) > 3:
                swing_highs.pop(0)

            if len(swing_highs) == 3:
                (i1, h1, r1), (i2, h2, r2), (i3, h3, r3) = swing_highs
                three_higher = h1 < h2 < h3
                diminishing = (h2 - h1) > (h3 - h2) if (h2 - h1) > 0 else False
                rsi_diverges = (
                    not np.isnan(r1) and not np.isnan(r3) and r3 < r1
                )
                if three_higher and diminishing and rsi_diverges:
                    if close_arr[i] < open_arr[i]:
                        # Wedge base target: most recent swing low before H1.
                        candidates = [sl for (idx, sl) in swing_lows_seen if idx < i1]
                        target = candidates[-1] if candidates else close_arr[i] * 0.95
                        in_pos = True
                        hold_days = 0
                        entry_stop = h3
                        entry_target = target
                        pos_arr[i] = -1
                        swing_highs = []
                        continue

        pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    pivot_window: int = 4,
    max_hold_days: int = 25,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        pivot_window=pivot_window,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
