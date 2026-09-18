"""Strategy: DecisionPoint 3-Timeframe Trend Model (Carl Swenlin) --
long-term/intermediate-term/short-term EMA-crossover regime alignment.

Hypothesis (see knowledge_base/strategies_log.jsonl for this id):
Per StockCharts.com ChartSchool's "DecisionPoint Trend Model"
(https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/decisionpoint-trend-model,
read via browser_exec fallback after web_search's DDGS backend could not
extract page content; Carl Swenlin's DecisionPoint methodology): trend
analysis across THREE simultaneous timeframes, each its own EMA-crossover
regime classifier, adapted to this repo's daily-bar-only data:
  - LONG-TERM: 50-EMA vs 200-EMA (source's own explicitly-stated daily-bar
    substitute for the primary monthly/weekly version) -- bull when
    50-EMA>200-EMA, bear otherwise.
  - INTERMEDIATE-TERM: 20-EMA vs 50-EMA -- bull when 20-EMA>50-EMA. Source's
    own refinement: a bearish 20/50 cross while 50-EMA is ALREADY below
    200-EMA is "especially bearish" (full sell/short signal); the SAME
    bearish 20/50 cross while 50-EMA is still ABOVE 200-EMA is merely
    "neutral" (the longer-term trend remains structurally bullish) --
    this asymmetric interpretation is the source's own distinctive
    contribution, not a generic triple-EMA-alignment rule.
  - SHORT-TERM: the 20-EMA's own slope direction (rising/falling).

Combined entry/exit logic (this repo's own mechanization of the source's
qualitative 3-timeframe synthesis): go long only when the long-term regime
is bullish (50-EMA>200-EMA) AND the intermediate-term regime is bullish
(20-EMA>50-EMA) AND the short-term 20-EMA slope is rising -- full 3-tier
alignment, the strongest of the source's stated regime combinations. Exit
to flat as soon as ANY of these three conditions breaks (the source's own
explicit "neutral" framing when only some conditions hold is treated
conservatively here as flat, not partial exposure, since a binary
generate_signals contract doesn't support a 3-state neutral tier without a
separate continuous-sizing variant).

Distinct from every prior EMA-crossover / triple-EMA-alignment strategy in
this repo (2026-09-04-070's Triple EMA, using three SIMULTANEOUS single-cross
EMAs 10/30/50 confirmed at the moment of one crossover event; the GMMA
cluster-spread strategy; and every simple dual-EMA-cross strategy) via this
being a genuinely 3-INDEPENDENT-CONDITION regime-alignment system spanning
distinct "long/intermediate/short-term" conceptual timeframes (50/200,
20/50, and 20-EMA-slope) with an asymmetric bear-severity distinction baked
into the source's own methodology, rather than one crossover event
confirmed by nearby EMA ordering.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _core(
    price_df: pd.DataFrame,
    long_fast: int = 50,
    long_slow: int = 200,
    inter_fast: int = 20,
    inter_slow: int = 50,
    slope_lookback: int = 5,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    ema_long_fast = close.ewm(span=long_fast, adjust=False).mean()
    ema_long_slow = close.ewm(span=long_slow, adjust=False).mean()
    ema_inter_fast = close.ewm(span=inter_fast, adjust=False).mean()
    ema_inter_slow = close.ewm(span=inter_slow, adjust=False).mean()

    long_bullish = ema_long_fast > ema_long_slow
    inter_bullish = ema_inter_fast > ema_inter_slow
    short_term_ema = ema_inter_fast  # 20-EMA doubles as the short-term trend line
    short_rising = short_term_ema > short_term_ema.shift(slope_lookback)

    aligned_bullish = long_bullish & inter_bullish & short_rising
    return aligned_bullish.astype(int)


def generate_signals(
    price_df: pd.DataFrame,
    long_fast: int = 50,
    long_slow: int = 200,
    inter_fast: int = 20,
    inter_slow: int = 50,
    slope_lookback: int = 5,
) -> pd.Series:
    return _core(price_df, long_fast, long_slow, inter_fast, inter_slow, slope_lookback)


def generate_returns(
    price_df: pd.DataFrame,
    long_fast: int = 50,
    long_slow: int = 200,
    inter_fast: int = 20,
    inter_slow: int = 50,
    slope_lookback: int = 5,
    leverage_cap: float = 1.0,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = _core(df, long_fast, long_slow, inter_fast, inter_slow, slope_lookback)
    daily_ret = close.pct_change().fillna(0.0)
    return leverage_cap * daily_ret * position.shift(1).fillna(0)
