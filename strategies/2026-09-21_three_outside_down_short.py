"""Strategy: Three Outside Down bearish-reversal short, trend+ATR gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-233):
Per QuantifiedStrategies.com's "Three Outside Down: Candlestick Pattern"
(https://www.quantifiedstrategies.com/three-outside-down-candlestick-pattern/,
read via browser_exec fallback -- web_extract's ddgs backend cannot extract
page content), the Three Outside Down is a 3-candle bearish reversal
pattern at the end of an uptrend, an extension/confirmation of the bearish
engulfing pattern:
  1. Candle 1: a small bullish candle (bulls losing steam within the
     preceding rally).
  2. Candle 2: a large bearish candle that engulfs candle 1 -- opens with
     a gap up but closes below candle 1's open (the "bearish engulfing"
     component).
  3. Candle 3: a bearish candle that opens below candles 1 & 2's lows and
     closes even lower (source's explicit "confirmation" bar).
Source claims this is one of the more reliable patterns in its 75-pattern
backtest study (~70% accuracy), best used with trend/resistance context
(trend lines, long-period MAs) but discloses no specific numeric
stop-loss/profit-target -- only generic "exit longs / short rallies"
guidance, so exits here use this repo's standard ATR stop/target
construction.

First "Three Outside Down" entry in this repo (0 prior hits) -- distinct
from "Three Outside Up" (2 prior hits under the "three outside up"
keyword, the bullish mirror-image already tried) and from plain Bearish
Engulfing (already tried in this repo) since Three Outside Down requires
the ADDITIONAL 3rd confirmation candle beyond the engulfing pair.

Operationalization:
  - Uptrend context: close[t-3] > SMA(trend_window) at candle 1 (source's
    "end of an uptrend" / "resistance level" requirement, proxied with a
    trend filter consistent with this repo's other candlestick
    strategies).
  - Candle 1 (t-2): bullish (close > open), small body (body <=
    small_body_max_pct of its own high-low range -- source's "small
    compared to other bullish candlesticks").
  - Candle 2 (t-1): bearish (close < open) AND engulfs candle 1: opens
    above candle 1's open (source's "gap up" open) AND closes below
    candle 1's open (source's explicit bearish-engulfing close
    requirement).
  - Candle 3 (t): bearish (close < open) AND opens below min(low[t-1],
    low[t-2]) AND closes below min(close[t-1], low[t-1], low[t-2])
    (source's explicit "opens below the prior two candles' lows, and
    closes even lower than the prior two candles' close" confirmation
    rule) -> entry short at candle 3's close.
  - Exit: this repo's standard ATR stop/target -- stop_price = max(candle
    1 high, candle 2 high) + atr_stop_mult * ATR, target_price = entry -
    target_atr_mult * ATR, with a max_hold_days time-stop fallback.

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
    small_body_max_pct: float = 0.4,
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
    uptrend = (c.shift(2) > sma.shift(2)).fillna(False)

    rng1 = (h.shift(2) - l.shift(2)).replace(0.0, 1e-12)
    body1 = (c.shift(2) - o.shift(2)).abs()
    candle1_small_bull = (c.shift(2) > o.shift(2)) & ((body1 / rng1) <= small_body_max_pct)

    candle1_open = o.shift(2)
    candle1_high = h.shift(2)
    candle1_low = l.shift(2)

    candle2_bearish = c.shift(1) < o.shift(1)
    candle2_engulfs = (o.shift(1) > candle1_open) & (c.shift(1) < candle1_open)
    candle2_high = h.shift(1)
    candle2_low = l.shift(1)
    candle2_close = c.shift(1)

    candle3_bearish = c < o
    prior_min_low = pd.concat([candle1_low, candle2_low], axis=1).min(axis=1)
    prior_min_close = pd.concat([candle2_close, candle1_low, candle2_low], axis=1).min(axis=1)
    candle3_opens_below = o < prior_min_low
    candle3_closes_lower = c < prior_min_close

    pattern_confirm = (
        uptrend
        & candle1_small_bull.fillna(False)
        & candle2_bearish.fillna(False)
        & candle2_engulfs.fillna(False)
        & candle3_bearish
        & candle3_opens_below.fillna(False)
        & candle3_closes_lower.fillna(False)
    ).fillna(False)

    stop_ref = pd.concat([candle1_high, candle2_high], axis=1).max(axis=1)
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
