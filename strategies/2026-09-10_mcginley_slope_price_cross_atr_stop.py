"""Strategy: Price crosses ABOVE a slope-confirmed single McGinley Dynamic
line, with ATR-based stop-loss and take-profit (risk:reward exit), rather
than a signal-based or fixed-hold exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-096):
Per https://www.forexcracked.com/education/mcginley-dynamic-forex-trading-strategy/
(ForexCracked's "McGinley Dynamic and Adaptive Forex Trading Strategy",
via browser_exec fallback -- web_search's DDGS backend returned a
RequestError/TLS unexpected-eof on the initial query this iteration), the
source's disclosed rule is: (1) confirm an uptrend via the McGinley Dynamic
line itself sloping upward, (2) enter long when price CLOSES above the MD
line (candle-close confirmation, not an intrabar touch), (3) place a stop
loss below the recent swing low / a few pips below the MD line, and (4) take
profit at either a prior resistance level or a fixed risk:reward multiple
(source explicitly offers "use a 1:2 risk-reward ratio" as the simplest
mechanical version).

This is a genuinely new variant of this repo's McGinley Dynamic family:
- 2026-09-04-127 (rejected near-miss): unconditional FAST/SLOW McGinley
  crossover (dual-line), no slope filter, no ATR stop.
- 2026-09-08-020 (accepted/tested): price crosses BELOW a single MD line
  as an OVERSOLD mean-reversion dip-buy with a fixed-day-count exit -- the
  opposite direction and a completely different exit mechanic.
- 2026-09-09-049 (rejected): fast/slow crossover + 200d SMA gate + vol-regime
  exit -- still dual-line, still signal-based exit.
This strategy is the first to trade price crossing ABOVE a SINGLE MD line
(trend-following, not mean-reversion) with an explicit slope-of-MD
confirmation filter AND a genuine ATR-based stop-loss/take-profit exit
(fixed risk:reward) instead of a signal-based or time-based exit -- directly
implementing the source's own disclosed risk-management rule rather than
approximating it away.

Signal logic
------------
- McGinley Dynamic (single line): MD[0] = close[0]; for t>0,
  MD[t] = MD[t-1] + (close[t] - MD[t-1]) / (md_period * (close[t]/MD[t-1])**4)
- Slope confirmation: MD is "rising" when MD[t] > MD[t-slope_lookback].
- Entry (long): close crosses from <= MD to > MD (today close>MD,
  yesterday close<=MD) AND MD is rising (slope filter, per source's
  "confirm the uptrend with the MD Indicator sloping upward" step).
- Stop-loss: ATR(atr_window) * stop_atr_mult below the entry-bar close,
  fixed at entry (source's "place stop-loss below the recent swing low /
  a few pips below the MD line").
- Take-profit: entry_close + stop_atr_mult*ATR*rr_ratio (source's own
  "use a 1:2 risk-reward ratio" -- rr_ratio default 2.0).
- Exit: whichever of {stop-loss hit, take-profit hit, close crosses back
  below a now-falling MD line, max_hold_days elapsed} triggers first,
  checked in that priority order each bar.
- Long-only, flat otherwise, no re-entry while already in a position.

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


def _mcginley_dynamic(close: pd.Series, period: int) -> pd.Series:
    md = pd.Series(index=close.index, dtype=float)
    md.iloc[0] = close.iloc[0]
    prev = close.iloc[0]
    for i in range(1, len(close)):
        c = close.iloc[i]
        if prev <= 0:
            prev = c
            md.iloc[i] = c
            continue
        ratio = c / prev
        denom = period * (ratio ** 4)
        if denom == 0 or pd.isna(denom):
            new_val = prev
        else:
            new_val = prev + (c - prev) / denom
        md.iloc[i] = new_val
        prev = new_val
    return md


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
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
    md_period: int = 20,
    slope_lookback: int = 5,
    atr_window: int = 14,
    stop_atr_mult: float = 1.5,
    rr_ratio: float = 2.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    md = _mcginley_dynamic(close, md_period)
    md_rising = md > md.shift(slope_lookback)
    md_falling = md < md.shift(slope_lookback)

    prev_close = close.shift(1)
    prev_md = md.shift(1)
    cross_above = (prev_close <= prev_md) & (close > md)
    cross_below = (prev_close >= prev_md) & (close < md)

    entry_signal = cross_above & md_rising.fillna(False)

    atr = _atr(df, atr_window)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0
    tp_price = 0.0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            c = close.iloc[i]
            stop_hit = c <= stop_price
            tp_hit = c >= tp_price
            signal_exit = bool(cross_below.iloc[i]) and bool(md_falling.fillna(False).iloc[i])
            if stop_hit or tp_hit or signal_exit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]) and not pd.isna(atr.iloc[i]) and atr.iloc[i] > 0:
                in_position = True
                entry_idx = i
                entry_close = close.iloc[i]
                risk = stop_atr_mult * atr.iloc[i]
                stop_price = entry_close - risk
                tp_price = entry_close + risk * rr_ratio
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
