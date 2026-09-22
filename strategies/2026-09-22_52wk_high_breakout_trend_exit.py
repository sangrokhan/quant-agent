"""Strategy: 52-week-high breakout momentum, with trend/trailing-stop exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-062):
Per QuantifiedStrategies.com's "52-Week High Trading Strategy (Backtest,
Trading Rules And Example)" (https://www.quantifiedstrategies.com/52-week-high-strategy/,
read via browser_exec this iteration -- web_search's DDGS backend
intermittently TLS-erroring), the "52-week high effect" (academic literature
cited: Hong/Jordan/Liu; George/Hwang) finds stocks near their 52-week highs
outperform those far from them, an anchoring-bias-driven under-reaction
effect. The article's own third-party backtest (enlightenedstocktrading.com)
tests buying new 52-week highs with three exit rules and reports the best
risk/reward from Exit 1: "hold until the stock crosses below the 200-day
moving average" (CAGR 8.6%, MDD 44%). First 52-week-high breakout strategy
in this repo (0 prior KB hits for "52 week high").

Signal logic
------------
- Long entry: today's close is a new N-day high (N=252 trading days ~= 52
  weeks) i.e. close >= rolling max(close, lookback_days) evaluated using the
  PRIOR bar's rolling max (so today's own close doesn't trivially satisfy
  its own max).
- Exit: close falls below SMA(trend_exit_window) (source's own best-reported
  exit rule) OR a trailing_stop_pct drawdown from the post-entry peak close
  (source's second disclosed exit variant, offered here as an additional
  risk control on top of the primary trend exit) OR a max_hold_days
  time-stop as a safety backstop.
- Flat otherwise. Long-only (no short per SAFETY.md scope).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 252,
    trend_exit_window: int = 200,
    trailing_stop_pct: float = 0.25,
    max_hold_days: int = 300,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    prior_high = close.shift(1).rolling(lookback_days, min_periods=max(20, lookback_days // 4)).max()
    new_high = (close >= prior_high).fillna(False)
    sma_trend = close.rolling(trend_exit_window).mean()
    trend_break = (close < sma_trend).fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = -1
    peak_close = None
    for i in range(len(df.index)):
        c = close.iloc[i]
        if not in_position:
            if bool(new_high.iloc[i]):
                in_position = True
                entry_idx = i
                peak_close = c
        else:
            peak_close = max(peak_close, c) if peak_close is not None else c
            held = i - entry_idx
            trailing_hit = (c <= peak_close * (1.0 - trailing_stop_pct)) if peak_close else False
            if bool(trend_break.iloc[i]) or trailing_hit or held >= max_hold_days:
                in_position = False
                peak_close = None
        position.iloc[i] = 1 if in_position else 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    lookback_days: int = 252,
    trend_exit_window: int = 200,
    trailing_stop_pct: float = 0.25,
    max_hold_days: int = 300,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        df,
        lookback_days=lookback_days,
        trend_exit_window=trend_exit_window,
        trailing_stop_pct=trailing_stop_pct,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
