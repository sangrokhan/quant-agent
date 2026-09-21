"""Strategy: Ladder Bottom bullish-reversal long, pullback-in-uptrend gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-234):
Per QuantifiedStrategies.com's "Ladder Bottom Candlestick Pattern: Backtest
Findings" (https://www.quantifiedstrategies.com/ladder-bottom-candlestick-pattern/,
read via browser_exec fallback -- web_extract's ddgs backend cannot extract
page content), the Ladder Bottom is a 5-candle bullish reversal pattern:
  1-3. Three consecutive long bearish candles with progressively LOWER
       opens and closes (resembles Three Black Crows -- ongoing
       downswing).
  4. A bearish candle but with a SHORT body and an upper wick (momentum
     weakening).
  5. A bullish candle that OPENS ABOVE candle 4's body (a gap up),
     confirming the reversal.
Source's own explicit recommendation: trade this pattern as an
end-of-PULLBACK signal within an ongoing UPTREND (not as a standalone
call at the bottom of a long-term downtrend) -- "it is better to use the
pattern to predict the end of a pullback in an uptrend." No specific
numeric stop-loss/profit-target is disclosed, only generic guidance to
confirm with RSI/trendlines/support and use other risk-management tools.

First "Ladder Bottom" entry in this repo (0 prior hits) -- distinct from
Three Black Crows (the first 3 candles resemble it, but Ladder Bottom
requires the additional short-bodied 4th candle AND the bullish gap-up
5th candle, making it a materially different, longer conjunction) and
from Matching Low (2026-09-21-218, prior iteration: 2-candle pattern with
a matching-close requirement, no gap, no 5-candle structure).

Operationalization:
  - Uptrend context (source's explicit "pullback in an uptrend" scoping):
    close[t-6] > SMA(trend_window) (price was in an uptrend before the
    pullback began).
  - Candles 1-3 (t-4, t-3, t-2): each bearish (close < open) with
    progressively lower opens and closes: open[t-4] > open[t-3] >
    open[t-2] AND close[t-4] > close[t-3] > close[t-2].
  - Candle 4 (t-1): bearish (close < open), short body (body <=
    short_body_max_pct of its own high-low range) with an upper wick
    (high - max(open,close) >= min_upper_wick_pct * range).
  - Candle 5 (t): bullish (close > open) AND opens above candle 4's body
    top: open[t] > max(open[t-1], close[t-1]) (source's explicit "gaps
    above the body of the fourth candlestick") -> entry long at candle
    5's close.
  - Exit: this repo's standard ATR stop/target -- stop_price = candle 3's
    low (the pattern's own low point) - atr_stop_mult * ATR buffer,
    target_price = entry + target_atr_mult * ATR, with a max_hold_days
    time-stop fallback.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: 1 long/0 flat)
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
    short_body_max_pct: float = 0.35,
    min_upper_wick_pct: float = 0.25,
    atr_period: int = 14,
    atr_stop_mult: float = 0.5,
    target_atr_mult: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {1, 0} long/flat position series."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    n = len(c)

    sma = c.rolling(trend_window).mean()
    uptrend_ctx = (c.shift(6) > sma.shift(6)).fillna(False)

    b1_bear = c.shift(4) < o.shift(4)
    b2_bear = c.shift(3) < o.shift(3)
    b3_bear = c.shift(2) < o.shift(2)
    progressively_lower = (
        (o.shift(4) > o.shift(3)) & (o.shift(3) > o.shift(2))
        & (c.shift(4) > c.shift(3)) & (c.shift(3) > c.shift(2))
    )
    three_black = (b1_bear & b2_bear & b3_bear & progressively_lower).fillna(False)

    rng4 = (h.shift(1) - l.shift(1)).replace(0.0, 1e-12)
    body4 = (o.shift(1) - c.shift(1)).abs()
    upper_wick4 = h.shift(1) - pd.concat([o.shift(1), c.shift(1)], axis=1).max(axis=1)
    candle4_ok = (
        (c.shift(1) < o.shift(1))
        & ((body4 / rng4) <= short_body_max_pct)
        & ((upper_wick4 / rng4) >= min_upper_wick_pct)
    ).fillna(False)

    candle4_body_top = pd.concat([o.shift(1), c.shift(1)], axis=1).max(axis=1)
    candle5_bull = c > o
    candle5_gap_up = o > candle4_body_top

    pattern_confirm = (
        uptrend_ctx
        & three_black
        & candle4_ok
        & candle5_bull
        & candle5_gap_up.fillna(False)
    ).fillna(False)

    pattern_low = l.shift(2)  # candle 3's low, the pattern's own low reference
    atr = _atr(df, atr_period)

    position = pd.Series(0, index=c.index, dtype=int)
    in_position = False
    hold_days_left = 0
    stop_price = None
    target_price = None

    for i in range(n):
        if in_position:
            hit_stop = l.iloc[i] <= stop_price
            hit_target = h.iloc[i] >= target_price
            hold_days_left -= 1
            if hit_stop or hit_target or hold_days_left <= 0:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if bool(pattern_confirm.iloc[i]):
            entry_price = c.iloc[i]
            entry_atr = atr.iloc[i]
            plow = pattern_low.iloc[i]
            if pd.notna(entry_atr) and entry_atr > 0 and pd.notna(plow):
                stop_price = plow - atr_stop_mult * entry_atr
                target_price = entry_price + target_atr_mult * entry_atr
                in_position = True
                hold_days_left = max_hold_days
                position.iloc[i] = 1
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
