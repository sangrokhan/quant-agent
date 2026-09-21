"""Strategy: Bearish Kicker candlestick reversal short, ATR stop/target exits.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-231):
Per QuantifiedStrategies.com's "Bearish Kicker Candlestick Pattern Trading
Strategy" (https://www.quantifiedstrategies.com/bearish-kicker-candlestick-pattern/,
read via browser_exec fallback -- web_extract's ddgs backend cannot extract
page content): a 2-candle bearish reversal pattern at the top of an uptrend.
Candle 1: a long bullish candle. Candle 2: a bearish candle that OPENS
ABOVE candle 1's high (a gap-up "exhaustion gap") and CLOSES AT OR BELOW
candle 1's midpoint (source's explicit numeric identification rule).
Source's own disclosed trade recommendation: "sell short or use a short
put option" once the pattern completes. The source's own candlestick study
reports only a 47% success rate for this pattern (explicitly called "not
a par[ticularly reliable pattern]" in the source text) and notes it is
rare -- this hypothesis is tested here despite that low prior, since the
source gives a precise, numeric, backtestable identification rule (unlike
e.g. Diamond Bottom/Top, rejected in a prior iteration this repo for lack
of one) and grid-testing across parameters/assets/regimes may still turn
up a viable configuration even if the source's own qualitative study did
not find one.

First "Bearish Kicker" entry in this repo (0 prior hits) -- distinct from
"Bullish Kicker" (4 prior hits, already-saturated opposite-direction
pattern: bearish day1 + bullish gap-up day2, entered long).

Operationalization:
  - Uptrend context: close[t-1] > SMA(trend_window) at candle 1 (source's
    "appears after an uptrend" / "top of an uptrend" requirement).
  - Candle 1 (t-1): bullish (close > open), body >= tall_body_min_pct of
    its own high-low range (source's "long bullish candle").
  - Candle 2 (t): bearish (close < open), opens above candle 1's high
    (gap_min_pct above it, source's explicit "opens above the high of the
    bullish candlestick"), and closes at or below candle 1's midpoint
    (source's explicit "closes at or below its midpoint").
  - Entry: short at candle 2's close (pattern completes and confirms on
    that same bar, per source's rule -- no separate confirmation candle
    is disclosed, unlike some other candlestick strategies in this repo).
  - Exit: this repo's standard ATR stop/target construction (source gives
    no specific numeric stop/target, only generic risk-management
    guidance) -- stop_price = candle 2's high + atr_stop_mult * ATR,
    target_price = entry - target_atr_mult * ATR, with a max_hold_days
    time-stop fallback.

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
    gap_min_pct: float = 0.0,
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
    uptrend = c.shift(1) > sma.shift(1)

    rng1 = (h.shift(1) - l.shift(1)).replace(0.0, 1e-12)
    body1 = (c.shift(1) - o.shift(1)).abs()
    candle1_bullish_tall = (c.shift(1) > o.shift(1)) & ((body1 / rng1) >= tall_body_min_pct)

    candle1_high = h.shift(1)
    candle1_mid = (h.shift(1) + l.shift(1)) / 2.0

    candle2_bearish = c < o
    gap_up_open = o >= candle1_high * (1.0 + gap_min_pct)
    closes_below_mid = c <= candle1_mid

    pattern_confirm = (
        uptrend.fillna(False)
        & candle1_bullish_tall.fillna(False)
        & candle2_bearish
        & gap_up_open.fillna(False)
        & closes_below_mid.fillna(False)
    ).fillna(False)

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
            if pd.notna(entry_atr) and entry_atr > 0:
                stop_price = h.iloc[i] + atr_stop_mult * entry_atr
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
