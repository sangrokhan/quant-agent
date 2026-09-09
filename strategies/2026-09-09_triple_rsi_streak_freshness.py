"""Strategy: Triple RSI (QuantifiedStrategies.com single-RSI streak-decline
variant): 5-day RSI oversold, 3-consecutive-day decline, and a "was not
already deeply oversold 3 days ago" freshness condition, gated by a
200-day SMA uptrend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-050):
Per QuantifiedStrategies.com's "Triple RSI Trading Strategy" (disclosed via
Google's AI-overview synthesis of the paywalled article, visited this
iteration -- search query
"Triple RSI strategy quantifiedstrategies trading rules"), the strategy's
"triple" refers to three simultaneous conditions applied to a SINGLE 5-day
RSI (not three different RSI periods, which is a different construction
already tested in this repo as 2026-09-09-093's 3/7/14 stacked-RSI
crossover):

1. RSI(5) is below an oversold threshold (source: 30) at today's close.
2. RSI(5) has declined for `decline_days` (source: 3) consecutive days
   (momentum of the oversold condition -- not just a single-day dip).
3. RSI(5) was still above a "not already exhausted" ceiling
   (`freshness_threshold`, source: 60) `freshness_lookback` (source: 3)
   trading days ago -- filters out prolonged, already-stale oversold
   stretches, only trading FRESH drops into oversold territory.
4. Close is above its 200-day SMA (broad uptrend context, source's own
   stated filter).

Entry: buy at close when all four conditions hold. Exit: RSI(5) recovers
above `exit_threshold`, or a `max_hold_days` time-stop (source's own
article doesn't disclose an explicit exit rule beyond mentioning "buy at
the close" -- an RSI-recovery exit is this repo's standard convention for
RSI mean-reversion setups, consistent with e.g. 2026-09-04-164's QS RSI
exit).

First single-RSI three-condition (level + streak + freshness) construction
in this repo -- distinct from every prior RSI entry (Connors RSI2,
QS RSI composite, stacked multi-period RSI, RSI divergence, RSI+BB/MACD
composites).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wilder_rsi(series: pd.Series, window: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 5,
    oversold_threshold: float = 30.0,
    decline_days: int = 3,
    freshness_threshold: float = 60.0,
    freshness_lookback: int = 3,
    exit_threshold: float = 60.0,
    trend_sma_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _wilder_rsi(close, rsi_window)
    trend_sma = close.rolling(trend_sma_window).mean()
    uptrend = close > trend_sma

    # Condition 2: RSI declined for `decline_days` consecutive days
    # (rsi[t] < rsi[t-1] < ... < rsi[t-decline_days+1]).
    rsi_diff = rsi.diff()
    declining_today = rsi_diff < 0
    declining_streak = declining_today.rolling(decline_days).sum() == decline_days

    # Condition 3: RSI was above freshness_threshold `freshness_lookback`
    # bars ago (not already deep in an extended oversold stretch).
    rsi_fresh = rsi.shift(freshness_lookback) > freshness_threshold

    entry_cond = (
        (rsi < oversold_threshold)
        & declining_streak.fillna(False)
        & rsi_fresh.fillna(False)
        & uptrend.fillna(False)
    )
    exit_cond = rsi > exit_threshold

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = bool(exit_cond.iloc[i]) if pd.notna(exit_cond.iloc[i]) else False
            if exit_now or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_cond.iloc[i]):
                in_pos = True
                hold_count = 0
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
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
