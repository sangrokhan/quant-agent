"""Strategy: Bill Williams' Accelerator Oscillator (AC) zero-line crossover
with 200-day trend filter and ATR-based stop/take-profit.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per this iteration's research (Tradeworks' Accelerator Oscillator guide),
AC = Awesome Oscillator (AO) - SMA(5, AO), where AO = SMA(5, median_price)
- SMA(34, median_price), median_price = (high+low)/2. AC measures the
"speed of the speed" of momentum -- it's a leading indicator that turns
before AO, which turns before price. Source's own "Strategy 1: AC
Zero-Line Crossover" rule: buy when AC crosses from below to above zero
(acceleration turning positive), filtered by only taking signals in the
direction of the prevailing trend (close above a 200-period SMA); stop
loss at the previous bar's low minus 1.5x ATR; take-profit at the
previous bar's close plus 3x ATR (2:1 reward:risk). Exit on reverse
zero-line cross, stop, or take-profit, whichever comes first. First
Accelerator Oscillator strategy in this repo -- distinct from Awesome
Oscillator (already tested 3x) since AC is a second-derivative
"acceleration of momentum" measure, not the momentum measure itself.

Signal logic
------------
- median_price = (high + low) / 2
- ao = SMA(5, median_price) - SMA(34, median_price)
- ac = ao - SMA(5, ao)
- Entry (long): ac crosses from <=0 to >0 AND close > SMA(trend_window)
  (source's own 200-period trend filter).
- Exit: ac crosses back from >0 to <=0, OR close <= entry-bar-anchored
  stop (prior bar's low - atr_stop_mult*ATR(atr_window), fixed at entry,
  per source's own rule using "previous bar" relative to the SIGNAL bar),
  OR close >= entry-bar-anchored take-profit (prior bar's close +
  atr_target_mult*ATR(atr_window)), OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    atr_window: int = 14,
    atr_stop_mult: float = 1.5,
    atr_target_mult: float = 3.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    median_price = (high + low) / 2.0

    ao = median_price.rolling(5).mean() - median_price.rolling(34).mean()
    ac = ao - ao.rolling(5).mean()

    ac_pos = ac > 0
    cross_up = ac_pos & (~ac_pos.shift(1).fillna(False))
    cross_down = (~ac_pos) & (ac_pos.shift(1).fillna(False))

    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    atr = _atr(df, atr_window)

    entry_signal = cross_up & uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = None
    target_price = None

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            c = close.iloc[i]
            if (
                bool(cross_down.iloc[i])
                or (stop_price is not None and c <= stop_price)
                or (target_price is not None and c >= target_price)
                or held >= max_hold_days
            ):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]) and i > 0 and not pd.isna(atr.iloc[i]):
                in_position = True
                entry_idx = i
                prev_low = low.iloc[i - 1]
                prev_close = close.iloc[i - 1]
                stop_price = prev_low - atr_stop_mult * atr.iloc[i]
                target_price = prev_close + atr_target_mult * atr.iloc[i]
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    atr_window: int = 14,
    atr_stop_mult: float = 1.5,
    atr_target_mult: float = 3.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns: position (lagged by 1 bar to avoid
    lookahead) times the underlying daily simple return."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        trend_window=trend_window,
        atr_window=atr_window,
        atr_stop_mult=atr_stop_mult,
        atr_target_mult=atr_target_mult,
        max_hold_days=max_hold_days,
    )
    strat_returns = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_returns
