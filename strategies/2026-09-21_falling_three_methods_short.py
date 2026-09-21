"""Strategy: Falling Three Methods bearish-continuation short, 2:1 R:R exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-229):
Per QuantifiedStrategies.com's "Falling Three Methods Candlestick Pattern:
Backtest Analysis" (https://www.quantifiedstrategies.com/falling-three-methods-candlestick-pattern/,
read via browser_exec fallback -- web_extract's ddgs backend cannot extract
page content), the Falling Three Methods is a 5-candle bearish continuation
pattern occurring in an established downtrend:
  1. A tall bearish candle (candle 1) continuing the downtrend.
  2-4. Three smaller bullish candles, each confined within candle 1's
       high-low range (temporary profit-taking pullback, not a genuine
       reversal).
  5. A tall bearish candle that closes below the pattern's low (breaking
     below candle 1's low), confirming bears remain in control.
Source's own disclosed trade rules: "Once the last candle of the pattern
forms and closes below the low of the preceding candles, you can enter a
short position... the stop loss is set above the high of the pattern and
2x of the size of the stop loss is used to arrive at the profit target."

This is the first "Falling Three Methods" entry in this repo (0 prior hits
in strategies_index.jsonl) -- distinct from "Rising Three Methods" (4 prior
hits, the bullish mirror-image already tried) and from other 3+ candle
continuation/reversal families already tried (Three White Soldiers, Three
Black Crows, Three Inside/Outside).

Operationalization of the source's qualitative rules into numeric,
backtestable parameters:
  - Downtrend context: close[t-5] < SMA(trend_window) at the start of the
    pattern (candle 1), i.e. close 5 bars before the confirmation candle is
    below its trailing trend average -- "existing downtrend" gate.
  - Candle 1 (t-4): tall bearish, body >= tall_body_min_pct of its own
    high-low range (close[t-4] < open[t-4]).
  - Candles 2-4 (t-3, t-2, t-1): each bullish (close > open) AND each
    candle's BODY (open and close) confined within candle 1's [low, high]
    range (source's "confined within the range of the first candle"
    containment rule, checked on the body rather than the full wick since
    full-wick containment is essentially never satisfied in noisy daily
    data and would make the pattern untestable).
  - Candle 5 (t): bearish (close < open) AND closes below candle 1's low
    (source's explicit breakout-confirmation trigger) -> entry short at
    candle 5's close.
  - Exit: stop_price = candle 1's high (source's disclosed stop location);
    target_price = entry - 2 * (stop_price - entry) (source's disclosed
    2:1 reward:risk target), with a max_hold_days time-stop fallback if
    neither level is hit (this repo's standard fallback pattern for
    candlestick strategies with a fixed stop/target but no explicit
    max-hold rule in the source).

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


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    tall_body_min_pct: float = 0.5,
    stop_buffer_pct: float = 0.0,
    reward_risk_mult: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {-1, 0} short/flat position series."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    n = len(c)

    sma = c.rolling(trend_window).mean()

    rng1 = (h - l).replace(0.0, 1e-12)
    body1 = (o - c).abs()
    candle1_bearish_tall = (c < o) & ((body1 / rng1) >= tall_body_min_pct)

    # Candles at t-3, t-2, t-1: bullish and confined within candle1's [low, high]
    def _confined_bullish(shift: int) -> pd.Series:
        # Confinement is checked on the candle BODY (open/close), not the
        # full wick range -- matches common practical operationalizations
        # of "confined within the range of the first candle" (requiring
        # full-wick containment is almost never satisfied in noisy daily
        # data and would make the pattern untestable).
        oo, cc = o.shift(shift), c.shift(shift)
        bullish = cc > oo
        confined = (oo <= h.shift(4)) & (cc <= h.shift(4)) & (oo >= l.shift(4)) & (cc >= l.shift(4))
        return (bullish & confined).fillna(False)

    mid_ok = _confined_bullish(3) & _confined_bullish(2) & _confined_bullish(1)

    downtrend_ctx = (c.shift(4) < sma.shift(4)).fillna(False)

    candle5_bearish = c < o
    breaks_low = c < l.shift(4)

    pattern_confirm = (
        downtrend_ctx
        & candle1_bearish_tall.shift(4).fillna(False)
        & mid_ok
        & candle5_bearish
        & breaks_low
    ).fillna(False)

    pattern_high = h.shift(4)  # candle 1's high -> stop reference

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
            ph = pattern_high.iloc[i]
            if pd.notna(ph):
                stop_price = ph * (1.0 + stop_buffer_pct)
                risk = stop_price - entry_price
                if risk > 0:
                    target_price = entry_price - reward_risk_mult * risk
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
