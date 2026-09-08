"""Strategy: Dual Heiken Ashi Smoothed trend-following (fast/slow color-flip).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-062):
Per ForexMT4Indicators' Dual Heiken Ashi strategy
(https://forexmt4indicators.com/dual-heiken-ashi-forex-trading-strategy/,
browser_exec fallback -- web_search DDGS errored/returned no results for
several direct queries this iteration), the "Heiken Ashi Smoothed" indicator
double-EMA-smooths the raw Heiken Ashi OHLC (first an EMA of the HA OHLC,
then a second EMA of that result), producing candles whose color encodes
local trend slope with much less noise than raw Heikin-Ashi. The source's
own dual-timeframe system uses a FAST smoothed-HA (period ~6) and a SLOW
smoothed-HA (period ~50): buy when (1) fast HA-smoothed is above slow
HA-smoothed, (2) slow HA-smoothed is bullish-colored (established uptrend
regime), and (3) fast HA-smoothed just flipped from bearish to bullish
color (fresh momentum trigger within that regime). This is genuinely
distinct from all 3 prior Heikin-Ashi strategies already tested in this
repo (2026-09-04-045: single raw-HA color-streak trend-following;
2026-09-05-051: raw-HA color-streak CONTRARIAN mean-reversion;
2026-09-05-081: plain EMA crossover merely FILTERED by single-HA color) --
none of those double-EMA-smooth the HA candles themselves into a dual
fast/slow trend system.

Signal logic
------------
- Compute raw Heikin-Ashi OHLC: HA_close = (O+H+L+C)/4; HA_open[0]=(O+C)/2,
  HA_open[t] = (HA_open[t-1]+HA_close[t-1])/2 (standard recursive formula).
- "Smoothed HA" for a given (period, period2): e1 = EMA(HA_close, period),
  e2 = EMA(e1, period2) -- a double-EMA smooth of the HA close series
  (approximating the source's MT4 double-MA construction on OHLC; we use
  HA_close as the representative series since the color-flip signal in the
  source is driven by the smoothed line's own slope/level, not by
  wick/body geometry).
- fast_smoothed = smoothed HA close at (fast_period, fast_period2).
- slow_smoothed = smoothed HA close at (slow_period, slow_period2).
- fast_bullish[t] = fast_smoothed[t] > fast_smoothed[t-1] (color = blue/up).
- slow_bullish[t] = slow_smoothed[t] > slow_smoothed[t-1].
- Entry (long): fast_smoothed > slow_smoothed AND slow_bullish AND
  fast_bullish just turned True from False (fresh flip).
- Exit: fast_smoothed crosses back below slow_smoothed, or fast turns
  bearish again, or a max_hold_days time-stop.
- Flat (no position) whenever not in an active long.

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5/6):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
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


def _heikin_ashi_close(df: pd.DataFrame) -> pd.Series:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    ha_close = (o + h + l + c) / 4.0
    return ha_close


def _smoothed_ha(ha_close: pd.Series, period: int, period2: int) -> pd.Series:
    e1 = ha_close.ewm(span=period, adjust=False).mean()
    e2 = e1.ewm(span=period2, adjust=False).mean()
    return e2


def generate_signals(
    price_df: pd.DataFrame,
    fast_period: int = 6,
    fast_period2: int = 2,
    slow_period: int = 50,
    slow_period2: int = 2,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    ha_close = _heikin_ashi_close(df)

    fast_smoothed = _smoothed_ha(ha_close, fast_period, fast_period2)
    slow_smoothed = _smoothed_ha(ha_close, slow_period, slow_period2)

    fast_bullish = fast_smoothed > fast_smoothed.shift(1)
    slow_bullish = slow_smoothed > slow_smoothed.shift(1)
    fast_above_slow = fast_smoothed > slow_smoothed

    fast_flip_up = fast_bullish & (~fast_bullish.shift(1).fillna(False))
    entry = fast_above_slow & slow_bullish & fast_flip_up

    exit_cond = (~fast_above_slow) | (~fast_bullish)

    entry_arr = entry.to_numpy()
    exit_arr = exit_cond.to_numpy()
    pos_arr = np.zeros(len(df), dtype=int)

    in_pos = False
    entry_idx = -1
    for i in range(len(df)):
        if in_pos:
            held = i - entry_idx
            if exit_arr[i] or held >= max_hold_days:
                in_pos = False
            else:
                pos_arr[i] = 1
        if not in_pos and entry_arr[i]:
            in_pos = True
            entry_idx = i
            pos_arr[i] = 1

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    fast_period: int = 6,
    fast_period2: int = 2,
    slow_period: int = 50,
    slow_period2: int = 2,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        fast_period=fast_period,
        fast_period2=fast_period2,
        slow_period=slow_period,
        slow_period2=slow_period2,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change()
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns = strat_returns.fillna(0.0)
    return strat_returns
