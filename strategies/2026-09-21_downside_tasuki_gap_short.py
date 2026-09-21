"""Strategy: Downside Tasuki Gap bearish-continuation short, ATR trail stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-232):
Per QuantifiedStrategies.com's "Downside Tasuki Gap Candlestick Pattern:
Backtest Analysis" (https://www.quantifiedstrategies.com/downside-tasuki-gap-candlestick-pattern/,
read via browser_exec fallback -- web_extract's ddgs backend cannot extract
page content), the Downside Tasuki Gap is a 3-candle bearish continuation
pattern in a downtrend:
  1. Candle 1: bearish.
  2. Candle 2: bearish, gapping DOWN below candle 1's low (a genuine
     unfilled gap).
  3. Candle 3: bullish, closing WITHIN the gap (above candle 2's
     open/high, but still below candle 1's low -- the gap is not fully
     closed, only partially filled).
Source's own disclosed rules:
  - Confirmation/entry: price closes below candle 3's low (a 4th bar) to
    confirm the downtrend is resuming -> enter short.
  - Stop-loss: above candle 3's high.
  - Exit: source suggests a trailing stop to ride the continuation as long
    as it persists (no fixed target disclosed).

This is the first "Tasuki" gap pattern tested in this repo in either
direction (1 prior hit for the bare keyword "tasuki" in
strategies_index.jsonl was a false-positive substring match, not an actual
prior Tasuki strategy -- verified via Stage-2 lookup finding no matching
id). Distinct from "Falling Three Methods" (2026-09-21-229, rejected this
cron trigger -- that pattern has 3 small bullish PULLBACK candles fully
confined within candle 1's range with no gap requirement; Tasuki instead
requires a genuine gap-down between candles 1-2 and only a single
retracement candle 3 that partially fills it).

Operationalization:
  - Downtrend context: close[t-3] < SMA(trend_window) at candle 1
    (source's "downward swing of a downtrend" requirement).
  - Candle 1 (t-3): bearish (close < open).
  - Candle 2 (t-2): bearish (close < open) AND gaps down below candle 1's
    low: high[t-2] < low[t-3] * (1 - gap_min_pct) (source's explicit "gaps
    down well below the low of the first candle").
  - Candle 3 (t-1): bullish (close > open) AND closes within the gap:
    open[t-2] < close[t-1] < low[t-3] (source's explicit "closing within
    the gap created by the first two candles" -- above candle 2's own
    trading range but still below candle 1's low, i.e. the gap remains
    only partially filled).
  - Confirmation (t): close < candle 3's low (source's explicit 4th-bar
    confirmation rule) -> entry short at that bar's close.
  - Exit: stop_price = candle 3's high (source's disclosed stop
    reference) + atr_stop_mult * ATR buffer; since the source discloses a
    trailing-stop exit rather than a fixed target, this is implemented as
    a chandelier-style trailing stop that ratchets down with each new
    lower low made while in position (trail_atr_mult * ATR above the
    lowest low reached since entry), plus a max_hold_days time-stop
    fallback.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: -1 short/0 flat)
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


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat(
        [(h - l).abs(), (h - prev_c).abs(), (l - prev_c).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    gap_min_pct: float = 0.0,
    atr_period: int = 14,
    atr_stop_mult: float = 0.5,
    trail_atr_mult: float = 2.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {-1, 0} short/flat position series."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    n = len(c)

    sma = c.rolling(trend_window).mean()
    downtrend = (c.shift(3) < sma.shift(3)).fillna(False)

    candle1_bearish = c.shift(3) < o.shift(3)
    candle1_low = l.shift(3)

    candle2_bearish = c.shift(2) < o.shift(2)
    gaps_down = h.shift(2) < candle1_low * (1.0 - gap_min_pct)

    candle3_bullish = c.shift(1) > o.shift(1)
    candle3_closes_in_gap = (c.shift(1) > o.shift(2)) & (c.shift(1) < candle1_low)
    candle3_low = l.shift(1)
    candle3_high = h.shift(1)

    pattern = (
        downtrend
        & candle1_bearish.fillna(False)
        & candle2_bearish.fillna(False)
        & gaps_down.fillna(False)
        & candle3_bullish.fillna(False)
        & candle3_closes_in_gap.fillna(False)
    ).fillna(False)

    confirm = c < candle3_low
    pattern_confirm = (pattern & confirm).fillna(False)

    atr = _atr(df, atr_period)

    position = pd.Series(0, index=c.index, dtype=int)
    in_position = False
    hold_days_left = 0
    stop_price = None
    lowest_low_since_entry = None

    for i in range(n):
        if in_position:
            lowest_low_since_entry = min(lowest_low_since_entry, l.iloc[i])
            trail_atr = atr.iloc[i]
            if pd.notna(trail_atr):
                new_stop = lowest_low_since_entry + trail_atr_mult * trail_atr
                stop_price = min(stop_price, new_stop)
            hit_stop = h.iloc[i] >= stop_price
            hold_days_left -= 1
            if hit_stop or hold_days_left <= 0:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = -1
            continue

        if bool(pattern_confirm.iloc[i]):
            entry_atr = atr.iloc[i]
            c3_high = candle3_high.iloc[i]
            if pd.notna(entry_atr) and pd.notna(c3_high):
                stop_price = c3_high + atr_stop_mult * entry_atr
                lowest_low_since_entry = l.iloc[i]
                in_position = True
                hold_days_left = max_hold_days
                position.iloc[i] = -1
                continue

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
