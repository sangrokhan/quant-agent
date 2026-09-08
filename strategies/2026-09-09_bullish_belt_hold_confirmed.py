"""Strategy: Bullish Belt Hold candlestick reversal (confirmed breakout entry).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-033):
Per Investopedia's Bullish Belt Hold explainer
(https://www.investopedia.com/terms/b/bullishbelthold.asp): a bullish belt
hold is a single-day candlestick that forms during a downtrend when price
opens at/near the low (a gap down below the prior day's close, similar to a
white Marubozu) and then rallies through the session to close near the
high, leaving little to no lower shadow and only a small upper shadow. This
signals a sharp bearish-to-bullish sentiment shift. The source's own
explicit trading rule is NOT to buy the pattern bar itself -- "an entry
should only be taken when the price trades above the high of the belt hold
candlestick" (a confirmation breakout on a SUBSEQUENT bar), with a stop at
the belt-hold candle's own midpoint (a tighter, source-suggested
alternative to a stop below the whole pattern). The source explicitly notes
the pattern "is not considered very reliable" alone and its "reliability is
enhanced if it forms near a support level" -- operationalized here as a
long-term downtrend/oversold-proxy gate (close below its SMA(trend_window))
required for the pattern bar itself, distinct from every prior
single-candle pattern already tested in this repo (Hammer, Dragonfly Doji,
Piercing Line, Morning Star, etc.) since the Belt Hold's defining feature
is a gap-down OPEN combined with a full-range rally to the close, not a
wick/shadow-based reversal signature.

Signal logic
------------
- Pattern bar detection (bar i): open[i] <= low[i-1] (gap down at/below the
  prior day's low, per source's "significant gap down at the open");
  close[i] > open[i] (bullish/white candle); upper shadow small
  (high[i]-close[i] <= upper_shadow_pct * (high[i]-low[i])); no/negligible
  lower shadow (open[i]-low[i] <= lower_shadow_pct * (high[i]-low[i]));
  gated by close[i-1] < SMA(trend_window)[i-1] (downtrend context, the
  source's own support-level/reliability caveat approximated as a
  below-trend regime).
- Entry (confirmation breakout, per source's OWN stated rule): the first
  subsequent bar j>i whose close exceeds the pattern bar's high
  (close[j] > high[i]), within confirm_window bars of the pattern.
- Exit: close crosses below the pattern bar's own midpoint
  ((high[i]+low[i])/2, the source's own suggested tighter stop), or a
  max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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
    upper_shadow_pct: float = 0.15,
    lower_shadow_pct: float = 0.05,
    confirm_window: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_, high, low, close = df["open"], df["high"], df["low"], df["close"]
    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()

    n = len(df)
    o = open_.values
    h = high.values
    l = low.values
    c = close.values
    sma = trend_sma.values

    # Identify pattern bars.
    pattern_bars = []
    for i in range(1, n):
        if pd.isna(sma[i - 1]):
            continue
        rng = h[i] - l[i]
        if rng <= 0:
            continue
        gap_down = o[i] <= l[i - 1]
        bullish = c[i] > o[i]
        upper_shadow_ok = (h[i] - c[i]) <= upper_shadow_pct * rng
        lower_shadow_ok = (o[i] - l[i]) <= lower_shadow_pct * rng
        downtrend_context = c[i - 1] < sma[i - 1]
        if gap_down and bullish and upper_shadow_ok and lower_shadow_ok and downtrend_context:
            pattern_bars.append({"idx": i, "high": h[i], "low": l[i], "mid": (h[i] + l[i]) / 2.0})

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0
    used = set()

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if c[i] < stop_price or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            for p_idx, p in enumerate(pattern_bars):
                if p_idx in used:
                    continue
                pat_i = p["idx"]
                if i <= pat_i or i > pat_i + confirm_window:
                    continue
                if c[i] > p["high"]:
                    in_position = True
                    entry_idx = i
                    stop_price = p["mid"]
                    used.add(p_idx)
                    position.iloc[i] = 1
                    break

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
