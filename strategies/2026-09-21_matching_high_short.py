"""Strategy: Matching High bearish-reversal short (downtrend-rally scoping).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-237):
Per QuantifiedStrategies.com's "Matching High Candlestick Pattern:
Backtest Findings" (https://www.quantifiedstrategies.com/matching-high-candlestick-pattern/,
read via browser_exec fallback -- web_extract's ddgs backend cannot
extract page content), the Matching High is a 2-candle pattern (mirror of
"Matching Low", already tested in this repo, id=2026-09-21-218/220-era):
  1. Candle 1: a long bullish candle in an upswing.
  2. Candle 2: a smaller bullish candle that opens LOWER than candle 1's
     close but closes at/near the SAME level as candle 1's close (the
     "matching closes" resistance test -- buyers failed to make a new
     high on the 2nd attempt).
Source's own explicit direction-scoping guidance (critical -- the source
notes this pattern is ambiguous and can mean either a bearish reversal OR
a bullish continuation depending on context): "If you want to use this
pattern to find bearish signals, look for the one that forms around a key
resistance level in an already existing DOWNTREND" (i.e. the pattern is a
rally/pullback WITHIN a downtrend, not a raw uptrend impulse wave -- the
latter instead favors the bullish-continuation reading, which this
strategy does NOT implement). Source's disclosed confirmation: the 3rd
candle must be bearish and close below the low of candle 1 or candle 2.
Source's disclosed stop-loss: above the high of the pattern. No fixed
numeric profit target disclosed.

First "Matching High" entry in this repo (0 prior hits) -- distinct from
Matching Low (bullish mirror, prior iteration this repo, 2-candle bearish
pair with matching CLOSES tested for a downside reversal in a downtrend)
by being scoped to the opposite direction/context (bullish pair tested for
a resistance-rejection short within a downtrend rally).

Operationalization:
  - Downtrend context: close[t-4] < SMA(trend_window) at a lookback before
    candle 1 (source's explicit "already existing downtrend" scoping for
    the bearish reading).
  - Candle 1 (t-2): bullish (close > open), tall body (body >=
    tall_body_min_pct of its own high-low range -- source's "long bullish
    candle").
  - Candle 2 (t-1): bullish (close > open), smaller body than candle 1
    (body <= candle 1's body), opens below candle 1's close (source's
    explicit "opens lower than the closing price of the previous day"),
    AND closes within match_tolerance_pct of candle 1's close (source's
    "same closing price" matching-close criterion).
  - Confirmation (t): bearish (close < open) AND closes below min(low[t-2],
    low[t-1]) (source's explicit "must close below the low of the first or
    second candle") -> entry short at candle t's close.
  - Exit: this repo's standard ATR stop/target -- stop_price = max(high[t-2],
    high[t-1]) + atr_stop_mult * ATR (source's disclosed "above the high of
    the pattern" reference), target_price = entry - target_atr_mult * ATR,
    with a max_hold_days time-stop fallback.

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
    tall_body_min_pct: float = 0.4,
    match_tolerance_pct: float = 0.003,
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
    downtrend = (c.shift(3) < sma.shift(3)).fillna(False)

    rng1 = (h.shift(2) - l.shift(2)).replace(0.0, 1e-12)
    body1 = (c.shift(2) - o.shift(2)).abs()
    candle1_bull_tall = (c.shift(2) > o.shift(2)) & ((body1 / rng1) >= tall_body_min_pct)
    candle1_close = c.shift(2)
    candle1_high = h.shift(2)
    candle1_low = l.shift(2)

    body2 = (c.shift(1) - o.shift(1)).abs()
    candle2_bull_small = (c.shift(1) > o.shift(1)) & (body2 <= body1)
    candle2_opens_below_c1_close = o.shift(1) < candle1_close
    candle2_matches_close = (c.shift(1) - candle1_close).abs() <= match_tolerance_pct * candle1_close.abs()
    candle2_high = h.shift(1)
    candle2_low = l.shift(1)

    pattern = (
        downtrend
        & candle1_bull_tall.fillna(False)
        & candle2_bull_small.fillna(False)
        & candle2_opens_below_c1_close.fillna(False)
        & candle2_matches_close.fillna(False)
    ).fillna(False)

    confirm_bearish = c < o
    pattern_low = pd.concat([candle1_low, candle2_low], axis=1).min(axis=1)
    confirm_breaks_low = c < pattern_low

    pattern_confirm = (pattern & confirm_bearish & confirm_breaks_low).fillna(False)
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
