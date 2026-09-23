"""Strategy: DeMark conditional pivot R1/S1 breakout, trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id): per
Senzoukria's "DeMark Pivots" indicator documentation
(https://senzoukria.com/indicators/demark-pivots, read via browser_exec this
iteration), Tom DeMark's pivot formula is CONDITIONAL on the prior session's
own direction (close vs open), unlike standard/Fibonacci/Camarilla pivots
which use the same fixed formula every day:
    if prior close < prior open:  X = H + 2*L + C   (bearish session: double-weight the low)
    if prior close > prior open:  X = 2*H + L + C   (bullish session: double-weight the high)
    if prior close == prior open: X = H + L + 2*C   (doji: double-weight the close)
    Pivot = X / 4;  R1 = X/2 - L;  S1 = X/2 - H
DeMark deliberately defines only ONE resistance and ONE support level (no
R2/R3) -- "the method deliberately offers one boundary per side" per the
source. This is the first DeMark/conditional-pivot strategy in this repo (0
prior KB hits for "DeMark pivot"), distinct from the already-tested
Camarilla/Woodie pivots (fixed, non-conditional formulas). The source's page
gives the exact calculation but not a specific trading rule, so the standard
industry convention (breakout above R1 signals continuation strength;
breakdown below S1 signals weakness) is applied here, per common pivot-point
trading practice (Investopedia/Capital.com's general pivot-point strategy
guidance also surfaced in this iteration's search results), gated by a
longer-term trend filter to keep this long-only per the {0,1} contract.

Signal logic
------------
- Compute yesterday's DeMark pivot/R1/S1 from yesterday's O/H/L/C (session
  = daily bar, since this repo has no intraday session-splitting logic).
- Entry (long): today's close crosses above yesterday's R1 (breakout above
  the DeMark resistance level) AND close > SMA(trend_window) (trend gate).
- Exit: close crosses back below the DAY'S OWN pivot (mean-reversion-to-
  pivot exit, the natural "no-man's-land" boundary DeMark's own doc
  describes as "price holding above or below it is the simplest statement
  this indicator makes"), OR the trend gate flips false, OR a max_hold_days
  time-stop.

Interface contract matches strategies/2026-09-03_bb_meanrev_qqq_volregime.py:
generate_signals(price_df, **params) -> pd.Series {0,1}
generate_returns(price_df, **params) -> pd.Series of daily strategy returns
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _demark_levels(df: pd.DataFrame) -> pd.DataFrame:
    """Compute DeMark pivot/R1/S1 for each bar based on the PRIOR bar's OHLC."""
    prev_open = df["open"].shift(1)
    prev_high = df["high"].shift(1)
    prev_low = df["low"].shift(1)
    prev_close = df["close"].shift(1)

    x_down = prev_high + 2 * prev_low + prev_close
    x_up = 2 * prev_high + prev_low + prev_close
    x_flat = prev_high + prev_low + 2 * prev_close

    x = pd.Series(float("nan"), index=df.index, dtype=float)
    down_mask = prev_close < prev_open
    up_mask = prev_close > prev_open
    flat_mask = prev_close == prev_open

    x = x.mask(down_mask.fillna(False), x_down)
    x = x.mask(up_mask.fillna(False), x_up)
    x = x.mask(flat_mask.fillna(False), x_flat)

    pivot = x / 4.0
    r1 = x / 2.0 - prev_low
    s1 = x / 2.0 - prev_high

    return pd.DataFrame({"pivot": pivot, "r1": r1, "s1": s1}, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    levels = _demark_levels(df)
    r1, pivot = levels["r1"], levels["pivot"]

    sma_trend = close.rolling(trend_window).mean()
    trend_gate = close > sma_trend

    breakout = (close.shift(1) <= r1.shift(1)) & (close > r1)
    entry_signal = breakout & trend_gate.fillna(False)

    exit_below_pivot = close < pivot

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_pivot = bool(exit_below_pivot.iloc[i]) if not pd.isna(exit_below_pivot.iloc[i]) else False
            trend_broke = not bool(trend_gate.iloc[i]) if not pd.isna(trend_gate.iloc[i]) else False
            if exit_pivot or trend_broke or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]) if not pd.isna(entry_signal.iloc[i]) else False:
                in_position = True
                entry_idx = i
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
