"""Strategy: Mean-Reversion Swing Trading, 50% pullback re-entry
(Ken Calhoun, TASC Dec 2016 article / Jan 2017 Traders Tips code).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-139):
Per Ken Calhoun's "Mean-Reversion Swing Trading" (TASC Dec 2016; TradeStation
EasyLanguage code disclosed at
https://traders.com/Documentation/FEEDbk_docs/2017/01/TradersTips.html),
the setup identifies a fresh chan_length-day extreme (a new rolling high or
low), then computes the 50% retracement level between that extreme and the
opposite band's most recent reference point (TriggerLine = 0.5 *
(HighRef + LowRef)). The source's own long entry rule requires: (1) the
setup state remains "LongOK" (most recent extreme was a new HIGH) for two
consecutive bars, (2) price closes back ABOVE the 50% trigger line (pulling
back from the high, then resuming upward through the midpoint -- a
"pullback entry into an established uptrend", despite the article's
"mean-reversion" framing referring to the pullback itself, not the overall
trend direction), and (3) close is above the MALength-day moving average
(trend confirmation). Exit uses the source's own channel-based bracket:
take profit at the upper band, stop at the lower band (this repo
substitutes a max_hold_days time-stop for the source's fixed-dollar
StopDollars, which isn't replicable with OHLCV-only bars).

Signal logic
------------
- upper_band = rolling max(high, chan_length); lower_band = rolling
  min(low, chan_length).
- long_ok = True whenever the CURRENT bar's high equals upper_band (a fresh
  high just printed); persists until a fresh low replaces it (source's own
  LongOK/ShortOK state machine).
- high_ref = the high value at the most recent fresh-high bar; low_ref =
  the low value at the most recent fresh-low bar (state carried forward).
- trigger_line = 0.5 * (high_ref + low_ref).
- ma = SMA(close, ma_length).
- Entry (long): long_ok has been true for >=2 consecutive bars AND close
  crosses over trigger_line AND close > ma.
- Exit: close crosses back below trigger_line, OR close < ma (trend
  filter breaks), OR max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    chan_length: int = 20,
    ma_length: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    upper_band = high.rolling(chan_length).max()
    lower_band = low.rolling(chan_length).min()
    ma = close.rolling(ma_length).mean()

    n = len(df)
    long_ok = pd.Series(False, index=df.index)
    high_ref = pd.Series(float("nan"), index=df.index)
    low_ref = pd.Series(float("nan"), index=df.index)

    cur_long_ok = False
    cur_high_ref = float("nan")
    cur_low_ref = float("nan")
    for i in range(n):
        h, l = high.iloc[i], low.iloc[i]
        ub, lb = upper_band.iloc[i], lower_band.iloc[i]
        if pd.notna(ub) and h >= ub:
            cur_high_ref = h
            cur_long_ok = True
        if pd.notna(lb) and l <= lb:
            cur_low_ref = l
            cur_long_ok = False
        long_ok.iloc[i] = cur_long_ok
        high_ref.iloc[i] = cur_high_ref
        low_ref.iloc[i] = cur_low_ref

    trigger_line = 0.5 * (high_ref + low_ref)
    long_ok_2bar = long_ok & long_ok.shift(1).fillna(False)

    cross_over_trigger = (close > trigger_line) & (close.shift(1) <= trigger_line.shift(1))
    entry = long_ok_2bar & cross_over_trigger.fillna(False) & (close > ma).fillna(False)

    exit_trigger_break = (close < trigger_line) & (close.shift(1) >= trigger_line.shift(1))
    exit_trend_break = close < ma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger_break.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
