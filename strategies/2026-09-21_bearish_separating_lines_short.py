"""Strategy: Bearish Separating Lines continuation short, ATR stop/target.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-236):
Per QuantifiedStrategies.com's "Bearish Separating Lines Candlestick
Pattern" (https://www.quantifiedstrategies.com/bearish-separating-lines-candlestick-pattern/,
read via browser_exec fallback -- web_extract's ddgs backend cannot
extract page content), the Bearish Separating Lines is a rare 2-candle
bearish CONTINUATION pattern occurring in a clear, established downtrend:
  1. Candle 1: a long bullish candle (a momentary bull pullback/relief
     rally within the downtrend).
  2. Candle 2: a long bearish candle that OPENS at approximately the SAME
     PRICE as candle 1's open (source's explicit "second candle opens near
     first candle's opening price"), opens below candle 1's open, and
     closes below candle 1's low -- i.e. the bulls' entire gain from
     candle 1 is erased in a single bearish candle starting from the same
     level.
Source's disclosed rules: entry is a sell order below candle 2's low; exit
is a stop-loss "a few pips/points below the low of the second candle" (no
specific numeric R:R disclosed, generic risk-management guidance only).
Source explicitly flags a genuine risk-management concern: the pattern can
be misread as a REVERSAL due to its bullish first candle, when it is
actually meant to be traded as continuation of the PRIOR downtrend.

This is the first "Separating Lines" pattern ACTUALLY implemented and
tested in this repo (a prior iteration, 2026-09-10-010, flagged it as a
candidate but never built/tested it, only cited saturation of an unrelated
MA-ribbon family that iteration). Distinct from "Bullish Counterattack
Lines" (2026-09-09/10 era, already rejected -- Counterattack requires
matching CLOSES between the two candles, not matching OPENS; Separating
Lines requires matching OPENS with the second candle's low breaking below
the first candle's low entirely).

Operationalization:
  - Downtrend context: close[t-3] < SMA(trend_window) at a lookback
    before candle 1 (source's explicit "only identified during a clear
    and defined downtrend" requirement).
  - Candle 1 (t-1): bullish (close > open), body >= tall_body_min_pct of
    its own high-low range (source's "relatively strong"/"long" bullish
    candle).
  - Candle 2 (t): bearish (close < open), body >= tall_body_min_pct of
    its own range, opens within open_match_tolerance_pct of candle 1's
    open (source's "opens at about the same price"), AND closes below
    candle 1's low (source's explicit "closes below its low") -> entry
    short at candle 2's close.
  - Exit: this repo's standard ATR stop/target -- stop_price = candle 1's
    high + atr_stop_mult * ATR, target_price = entry - target_atr_mult *
    ATR, with a max_hold_days time-stop fallback.

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
    tall_body_min_pct: float = 0.5,
    open_match_tolerance_pct: float = 0.003,
    atr_period: int = 14,
    atr_stop_mult: float = 1.0,
    target_atr_mult: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {-1, 0} short/flat position series."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    n = len(c)

    sma = c.rolling(trend_window).mean()
    downtrend = (c.shift(2) < sma.shift(2)).fillna(False)

    rng1 = (h.shift(1) - l.shift(1)).replace(0.0, 1e-12)
    body1 = (c.shift(1) - o.shift(1)).abs()
    candle1_bullish_tall = (c.shift(1) > o.shift(1)) & ((body1 / rng1) >= tall_body_min_pct)

    candle1_open = o.shift(1)
    candle1_low = l.shift(1)

    rng2 = (h - l).replace(0.0, 1e-12)
    body2 = (o - c).abs()
    candle2_bearish_tall = (c < o) & ((body2 / rng2) >= tall_body_min_pct)

    opens_match = (o - candle1_open).abs() <= open_match_tolerance_pct * candle1_open.abs()
    closes_below_low = c < candle1_low

    pattern_confirm = (
        downtrend
        & candle1_bullish_tall.fillna(False)
        & candle2_bearish_tall
        & opens_match.fillna(False)
        & closes_below_low.fillna(False)
    ).fillna(False)

    stop_ref = h.shift(1)
    atr = _atr(df, atr_period)

    position = pd.Series(0, index=c.index, dtype=int)
    in_position = False
    hold_days_left = 0
    stop_price = None
    target_price = None

    for i in range(n):
        if in_position:
            hit_stop = h.iloc[i] >= stop_price
            hit_target = l.iloc[i] <= target_price
            hold_days_left -= 1
            if hit_stop or hit_target or hold_days_left <= 0:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = -1
            continue

        if bool(pattern_confirm.iloc[i]):
            entry_price = c.iloc[i]
            entry_atr = atr.iloc[i]
            sref = stop_ref.iloc[i]
            if pd.notna(entry_atr) and entry_atr > 0 and pd.notna(sref):
                stop_price = sref + atr_stop_mult * entry_atr
                target_price = entry_price - target_atr_mult * entry_atr
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
