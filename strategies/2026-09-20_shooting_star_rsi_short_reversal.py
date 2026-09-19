"""Strategy: Shooting Star candlestick reversal short, RSI-overbought confirmed.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per quantifiedstrategies.com's "Shooting Star Candlestick Pattern:
(Statistics, Facts, & Historical Backtest)" (visited this iteration via
browser_exec fallback -- web_search DDGS backend was hitting repeated
TLS/connection-reset errors and timeouts on every query attempted this
iteration), the Shooting Star (small body near the LOW of the day's range,
long upper shadow >= ~2x body, little/no lower shadow, occurring after an
upswing/at a resistance level) is a bearish reversal pattern: "an asset's
market price is pushed up quite significantly but then gets rejected at
higher prices, which indicates that the price may be about to decline."
The source's own recommended combination approach explicitly pairs the
pattern with "oscillators" for confirmation: "the overbought signal in an
oscillator can be combined with the shooting star pattern to generate a
short-selling signal", and with moving averages/trendlines as the dynamic
resistance context ("moving averages help you to find the trend and can
serve as dynamic resistance levels where a pullback can reverse from").

This strategy implements exactly that mechanical combination (deliberately
mirroring this repo's already-accepted-methodology Hanging Man/RSI short
reversal construction, id=2026-09-11-116, but using the SHOOTING STAR shape
-- long upper shadow near a LOW body, i.e. the geometric inverse of the
Hanging Man's long lower shadow):
  1. Uptrend/resistance context: close > SMA(trend_window) (the "upswing"
     the source requires the pattern to occur after).
  2. Shooting Star candle: body <= body_max_pct of the day's range, upper
     shadow >= shadow_ratio * body (source: "about twice or more the size
     of the body"), lower shadow <= body (source: "little or no lower
     wick").
  3. RSI(rsi_period) was >= rsi_overbought within the last rsi_lookback
     bars and is now falling (RSI today < RSI yesterday) -- the source's
     "oscillator's overbought signal" confirmation.
  4. Entry: short at next bar's close when all three conditions align.
  5. Exit: close crosses back below/to the SMA(trend_window) (source's own
     "ride the trend" target being the moving-average support), or a
     max_hold_days time-stop, whichever comes first.

First Shooting Star strategy in this repo (0 prior entries in
strategies_index.jsonl for "Shooting Star" as of this iteration); distinct
from the already-tested Hanging Man (long LOWER shadow, small body at TOP
of range) via its geometric inverse (long UPPER shadow, small body at
BOTTOM of range), and distinct from every other prior candlestick-family
entry (Piercing Line, Tweezer, Dark Cloud, Morning/Evening Star, Doji,
Marubozu, Harami, Engulfing, Three White Soldiers) which use different
shape/multi-candle definitions.

Source: https://www.quantifiedstrategies.com/shooting-star-candlestick-pattern/
(read via browser_exec; the source's own numeric backtest -- 705 trades,
Sharpe 1.35, since 1993 on SPY, is paywalled/"for members only" for the
exact bar-by-bar rules; this repo's mechanical rules are our own concrete
adaptation of the source's disclosed pattern-shape definition and its own
"combine with an oscillator for confirmation" prose guidance, not a
reproduction of the paywalled numeric ruleset).

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


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    body_max_pct: float = 0.30,
    shadow_ratio: float = 2.0,
    rsi_period: int = 14,
    rsi_overbought: float = 70.0,
    rsi_lookback: int = 3,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {-1, 0} short/flat position series."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]

    sma = c.rolling(trend_window).mean()
    uptrend = c > sma

    rng = (h - l).replace(0.0, 1e-12)
    body = (c - o).abs()
    body_pct = body / rng
    # Shooting Star: small body near the LOW of the range, long UPPER shadow,
    # little/no LOWER shadow -- geometric inverse of the Hanging Man.
    upper_shadow = h - df[["open", "close"]].max(axis=1)
    lower_shadow = df[["open", "close"]].min(axis=1) - l

    is_shooting_star = (
        (body_pct <= body_max_pct)
        & (upper_shadow >= shadow_ratio * body.replace(0.0, 1e-12))
        & (lower_shadow <= body.replace(0.0, 1e-12) * 1.0 + 1e-9)
    )

    rsi = _rsi(c, rsi_period)
    was_overbought = rsi.rolling(rsi_lookback).max() >= rsi_overbought
    rsi_falling = rsi < rsi.shift(1)

    entry = (
        uptrend.fillna(False)
        & is_shooting_star.fillna(False)
        & was_overbought.fillna(False)
        & rsi_falling.fillna(False)
    )
    exit_meanrev = c <= sma

    position = pd.Series(0, index=c.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(c)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = -1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = -1
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
