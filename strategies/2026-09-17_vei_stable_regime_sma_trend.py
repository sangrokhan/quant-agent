"""Strategy: SMA trend-following gated by the Volatility Expansion Index
(VEI = ATR(short)/ATR(long) stability filter).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-179):
Per a disclosed r/algotrading post with full Pine Script source
("The Signal I Use to Detect Hidden Instability in Markets", 
u/Prabuddha-Peramuna, https://www.reddit.com/r/algotrading/comments/1phv4zz/,
read this iteration via browser_exec after web_search DDGS backend
errored): VEI = ATR(10) / ATR(50) measures short-term volatility relative
to its own longer-term baseline. VEI < 1.0 marks a "stable/controlled"
regime where "trend setups behave well" and "pullbacks are respected";
VEI > 1.2 marks a "volatility expansion / unstable" regime where "trends
becoming noisy, fakeouts and broken structure, stops getting hit more
often." The source explicitly frames VEI as a REGIME FILTER, not a
standalone signal ("VEI is NOT a buy/sell signal... it tells you whether
entering makes sense"), so this strategy pairs it with a plain SMA
trend-following entry (this repo's most common baseline signal) exactly
as the source's own community backtest thread did (a top comment reports
independent walk-forward testing of "VEI < 1.0" as an entry filter across
44 futures markets). This is distinct from every other volatility-regime
filter in this repo: unlike HVR (2026-09-06-109, ratio of realized-vol
STD-DEVs of log returns) or ATR-expansion (2026-09-05-055, single ATR vs
its own rolling AVERAGE), VEI is a ratio of two DIFFERENT-LENGTH ATR
values themselves (a "fast ATR vs slow ATR" construction, not a
volatility-vs-its-own-history construction).

Signal logic
------------
- ATR(atr_short) and ATR(atr_long) via the standard Wilder true-range
  average (atr_short=10, atr_long=50 per source's own "best universal
  settings").
- VEI = ATR(atr_short) / ATR(atr_long).
- Stable regime: VEI (as of yesterday's close, causal) < vei_threshold
  (source's own stable-zone boundary, default 1.0).
- Entry (long): close > SMA(trend_window) (source's own suggested pairing:
  "trend setups behave well" in the stable zone) AND we are in the stable
  regime.
- Exit: close crosses back below SMA(trend_window), OR the regime flips to
  unstable (VEI >= vei_threshold, risk-off exit per source's own guidance
  to "reduce position size / skip entries / avoid trend continuations"
  when unstable), OR a max_hold_days time-stop.
- Flat otherwise; long-only, single position at a time.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_short: int = 10,
    atr_long: int = 50,
    vei_threshold: float = 1.0,
    trend_window: int = 100,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    atr_s = _atr(df, atr_short)
    atr_l = _atr(df, atr_long)
    vei = atr_s / atr_l
    # Causal: use yesterday's VEI reading to gate today's entry/hold.
    stable = (vei < vei_threshold).shift(1).fillna(False)

    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_days = 0

    for i in range(n):
        px_close = close.iloc[i]
        sma = trend_sma.iloc[i]
        is_stable = bool(stable.iloc[i]) if stable.iloc[i] == stable.iloc[i] else False

        if in_position:
            hold_days += 1
            trend_break = (sma == sma) and (px_close < sma)
            if trend_break or (not is_stable) or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if sma == sma and px_close > sma and is_stable:
            in_position = True
            hold_days = 0
            position.iloc[i] = 1
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
