"""Strategy: No-Wick Level Retest, gated by daily SMA trend filter, ATR TP/SL.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-048):
Per LuxAlgo's "No-Wick Retest Levels" indicator concept
(https://www.luxalgo.com/library/indicator/no-wick-retest-levels/, published
Sep 9 2026, read via browser_exec this iteration -- web_search DDGS backend
TLS-errored on all queries). A candle with little-to-no wick on the LOW side
(low close to open/close, i.e. the low IS effectively the candle's open or
close) marks a bar where sellers pushed price down and buyers/aggressive
initiators absorbed all the way to the close with no further downside
rejection -- interpreted by the source as a strong-momentum/exhaustion
"institutional footprint" level. The bar's own low becomes an "untapped
level" that, when price later retests it (a later bar's low comes back down
near that level) while a trend filter still agrees, offers a high-probability
long re-entry. The source's own construction uses a 1-minute EMA trend
filter and is designed for intraday charts (already flagged infeasible on
this repo's daily-bar-only data/loaders.py in prior KB entry 2026-09-17-015)
-- this adaptation substitutes a daily SMA(trend_window) trend filter in
place of the source's 1-min EMA, keeping the core no-wick-level + retest +
ATR-based exit mechanism otherwise unchanged. Distinct from the already-
rejected Marubozu breakout strategy (2026-09-06-146, which enters on a
BREAKOUT above the marubozu bar's high) since this is a RETEST/retrace INTO
a level from a later pullback, not a breakout continuation.

Signal logic
------------
- A "no-wick-down" bar: (low - min(open, close)) <= wick_tolerance_pct x
  (high - low), i.e. the bar's lower wick is negligible relative to its own
  range -- the low is essentially at the open or close.
- That bar's own low becomes a level, valid for level_expiry_bars.
- Entry (long): a later bar's low retests the level (low <= level x
  (1 + retest_tolerance_pct)) while close > SMA(trend_window) (source's
  trend-filter requirement, adapted to daily bars).
- Exit: ATR-based take-profit (entry_price + tp_atr_mult x ATR) or
  stop-loss (entry_price - sl_atr_mult x ATR), whichever hits first, or a
  max_hold_days time-stop backstop (not in source, added by this repo for a
  bounded holding period).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

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
    wick_tolerance_pct: float = 0.1,
    retest_tolerance_pct: float = 0.005,
    level_expiry_bars: int = 20,
    trend_window: int = 100,
    atr_window: int = 14,
    tp_atr_mult: float = 2.0,
    sl_atr_mult: float = 1.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    n = len(df)
    open_ = df["open"].values
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    atr = _atr(df, atr_window).values

    sma = df["close"].rolling(trend_window).mean()
    uptrend = (df["close"] > sma).values

    position = pd.Series(0, index=df.index, dtype=int)

    # Find no-wick-down bars and their (level, expiry) tuples, chronological.
    levels = []  # (formed_idx, level_price, expiry_idx)
    for i in range(n):
        rng = high[i] - low[i]
        if rng <= 0:
            continue
        body_low = min(open_[i], close[i])
        lower_wick = body_low - low[i]
        if lower_wick <= wick_tolerance_pct * rng:
            expiry_idx = min(n - 1, i + level_expiry_bars)
            levels.append((i, low[i], expiry_idx))

    levels.sort(key=lambda z: z[0])
    lvl_ptr = 0
    active_levels = []

    in_position = False
    entry_idx = None
    entry_price = None

    for i in range(n):
        while lvl_ptr < len(levels) and levels[lvl_ptr][0] <= i:
            _, lvl, exp = levels[lvl_ptr]
            active_levels.append((lvl, exp))
            lvl_ptr += 1
        active_levels = [z for z in active_levels if z[1] >= i]

        if in_position:
            held = i - entry_idx
            a = atr[i]
            tp_price = entry_price + tp_atr_mult * a if a and not pd.isna(a) else None
            sl_price = entry_price - sl_atr_mult * a if a and not pd.isna(a) else None
            hit_tp = tp_price is not None and high[i] >= tp_price
            hit_sl = sl_price is not None and low[i] <= sl_price
            time_exit = held >= max_hold_days
            if hit_tp or hit_sl or time_exit:
                in_position = False
                entry_idx = None
                entry_price = None
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
            continue

        if not bool(uptrend[i]) if not pd.isna(uptrend[i]) else True:
            position.iloc[i] = 0
            continue

        entered = False
        for lvl, exp in active_levels:
            if low[i] <= lvl * (1.0 + retest_tolerance_pct):
                entered = True
                break
        if entered:
            in_position = True
            entry_idx = i
            entry_price = close[i]
            position.iloc[i] = 1
        else:
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
