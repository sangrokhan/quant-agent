"""Strategy: Larry Williams Volatility Breakout (daily-bar day-trade variant).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-094):
Larry Williams' classic volatility breakout system: each day's long entry
target = today's open + k * (previous day's high - previous day's low).
If price trades up through that target intraday, go long and exit at the
day's close (day-trade); otherwise stay flat that day. Sources (TradingView,
WHSelfInvest, tistory.com) converge on k in the 0.25-0.5 range. The
hypothesis: on liquid trend-prone assets (crypto especially, which trades
24/7 with no overnight gap-fill mechanism equities have), the day after an
average/narrow range tends to see a genuine volatility expansion in the
breakout direction, giving this simple rule positive edge net of the
day-trade round-trip.

Signal logic (daily-bar approximation of the intraday original)
-----------------------------------------------------------------
- prior_range = high[t-1] - low[t-1]
- target[t] = open[t] + k * prior_range
- Entered if high[t] >= target[t] (i.e. price traded up through the target
  intraday) -- this is the closest daily-bar-only approximation of "long
  entry triggered when price crosses above the target", since we don't have
  intraday bars to detect the exact crossing time.
- If entered: exit at close[t] (day-trade, no overnight hold) -- return for
  that day = close[t]/target[t] - 1.
- If not entered (high[t] < target[t]): flat that day, return 0.
- No look-ahead: target[t] only depends on open[t] and yesterday's
  high/low, all known before or at today's open.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position,
        1 on days the breakout was triggered)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _breakout_frame(price_df: pd.DataFrame, k: float) -> pd.DataFrame:
    df = _prep(price_df)
    prior_high = df["high"].shift(1)
    prior_low = df["low"].shift(1)
    prior_range = (prior_high - prior_low).fillna(0.0)
    target = df["open"] + k * prior_range
    entered = df["high"] >= target
    return pd.DataFrame({
        "target": target,
        "entered": entered,
        "close": df["close"],
    }, index=df.index)


def generate_signals(price_df: pd.DataFrame, k: float = 0.5) -> pd.Series:
    """Return a {0,1} position series (1 on days the breakout triggered)."""
    frame = _breakout_frame(price_df, k)
    return frame["entered"].astype(int)


def generate_returns(price_df: pd.DataFrame, k: float = 0.5) -> pd.Series:
    """Day-trade returns: close[t]/target[t] - 1 on entered days, else 0."""
    frame = _breakout_frame(price_df, k)
    ret = pd.Series(0.0, index=frame.index)
    entered_mask = frame["entered"] & (frame["target"] > 0)
    ret.loc[entered_mask] = (frame.loc[entered_mask, "close"] / frame.loc[entered_mask, "target"]) - 1.0
    return ret
