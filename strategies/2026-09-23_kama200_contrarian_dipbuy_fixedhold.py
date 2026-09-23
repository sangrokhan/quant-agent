"""Strategy: 200-day KAMA contrarian dip-buy, fixed 200-trading-day hold.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-... this
iteration): Per QuantifiedStrategies.com's "The 200-Day KAMA Strategy: A
Surprisingly Strong Backtest" (Sept 2026, disclosed via its own
Facebook/LinkedIn/YouTube/X promo copy read via browser_exec Google SERP
fallback this iteration -- web_search returned no usable direct-article
result for the KAMA-specific query): the source's own disclosed rule for
SPY is "buy at the close when [price] crosses below the [200-day KAMA],
and exit after 200 trading days" -- i.e. a CONTRARIAN dip-buy against the
long-horizon adaptive trend line, held for a long fixed period rather than
exited on a trend-following signal reversal. Source claims a 10.52% average
gain per trade in its own SPY historical backtest. This is economically
distinct from every prior KAMA strategy in this repo (2026-09-04-048/151,
2026-09-06-181/183, 2026-09-16/17/19 crossovers/dual-KAMA/AMA-crossover
variants), all of which are TREND-FOLLOWING (buy when price is ABOVE a
rising KAMA); this is the first KAMA-based MEAN-REVERSION/dip-buy strategy
in this repo, using the 200-day KAMA specifically as a long-horizon "fair
value" anchor to buy weakness against, with a fixed long hold rather than a
signal-based exit.

Signal logic
------------
- KAMA(200) computed with the standard Kaufman efficiency-ratio adaptive
  smoothing constant (identical construction to this repo's existing KAMA
  strategies, er_window/fast_period/slow_period tunable, default kama
  period itself set by er_window+slow_period conventions -- see _kama()).
- Entry (long): close crosses from >= KAMA(200) to < KAMA(200) on this bar
  (a fresh dip below the long-horizon adaptive average -- the source's own
  "crosses below" trigger, not a sustained-below state).
- Exit: fixed hold_days trading days after entry (source's own disclosed
  200-trading-day hold; kept as a tunable parameter here for the grid test
  rather than hardcoding 200), with no earlier signal-based exit (this
  matches the source's own bare rule -- a max_hold_days-only exit).
- No pyramiding: while a position is open, additional dip-below crossings
  are ignored until the current hold completes.

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


def _kama(close: pd.Series, er_window: int, fast_period: int, slow_period: int) -> pd.Series:
    change = (close - close.shift(er_window)).abs()
    volatility = close.diff().abs().rolling(er_window).sum()
    er = (change / volatility.replace(0.0, np.nan)).fillna(0.0)

    fast_sc = 2.0 / (fast_period + 1)
    slow_sc = 2.0 / (slow_period + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    kama = np.empty(len(close))
    kama[:] = np.nan
    close_arr = close.to_numpy()
    sc_arr = sc.to_numpy()

    first_valid = er_window
    if first_valid >= len(close):
        return pd.Series(kama, index=close.index)
    kama[first_valid] = close_arr[first_valid]
    for i in range(first_valid + 1, len(close)):
        prev = kama[i - 1]
        if np.isnan(prev):
            kama[i] = close_arr[i]
        else:
            kama[i] = prev + sc_arr[i] * (close_arr[i] - prev)

    return pd.Series(kama, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    er_window: int = 200,
    fast_period: int = 2,
    slow_period: int = 30,
    hold_days: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    kama = _kama(close, er_window, fast_period, slow_period)

    below = (close < kama).fillna(False)
    at_or_above_prev = (~below.shift(1).fillna(False))
    cross_below = (below & at_or_above_prev).to_numpy()

    n = len(df)
    pos_arr = np.zeros(n, dtype=int)
    in_pos = False
    entry_idx = -1
    for i in range(n):
        if in_pos:
            held = i - entry_idx
            if held >= hold_days:
                in_pos = False
            else:
                pos_arr[i] = 1
        if not in_pos and cross_below[i]:
            in_pos = True
            entry_idx = i
            pos_arr[i] = 1

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    er_window: int = 200,
    fast_period: int = 2,
    slow_period: int = 30,
    hold_days: int = 200,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        er_window=er_window,
        fast_period=fast_period,
        slow_period=slow_period,
        hold_days=hold_days,
    )
    daily_returns = df["close"].pct_change()
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns = strat_returns.fillna(0.0)
    return strat_returns
