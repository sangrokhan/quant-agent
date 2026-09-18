"""Strategy: Weekly-timeframe Wilder RSI(14) 30/70 threshold crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-012):
Per multiple corroborating sources (TrendSpider AI-overview synthesis,
ThePatternSite.com's "Bulkowski's Review of Wilder's RSI", Steema/other
standard RSI references): Wilder's classic 14-period RSI with 30/70
thresholds is most commonly described on a DAILY chart, but is also widely
applied on a WEEKLY chart for swing/position trading with materially less
whipsaw than the daily version, since it only re-evaluates once per
completed week. This repo has 30+ prior DAILY-bar RSI variants (threshold
crossover, divergence, 2-period, streak-family, continuous-sizing dials,
etc.) but has NEVER tested the plain classic 14/30/70 rule computed on
weekly-RESAMPLED bars -- a genuinely different signal-generation frequency,
not just a different threshold or smoothing choice on the same daily
series. Long entry when weekly RSI(14) crosses back above 30 (recovering
from oversold); exit when weekly RSI(14) crosses back below 70 having
been overbought (i.e., a classic swing-trade oscillation capture), held
via daily bars in between the weekly re-evaluations.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wilder_rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-12)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Weekly-resampled Wilder RSI(rsi_period): long entry when weekly RSI
    crosses back above `oversold` from below; exit when weekly RSI crosses
    back below `overbought` having been at/above it (classic oscillation
    capture -- ride the swing from oversold-recovery to overbought-rollover).
    The weekly decision is forward-filled onto daily bars in between
    weekly closes (signal only re-evaluates once per completed week).
    """
    df = _prep(price_df)
    close = df["close"]

    weekly_close = close.resample("W").last().dropna()
    weekly_rsi = _wilder_rsi(weekly_close, rsi_period)

    # State machine on the WEEKLY series: long while RSI has crossed back
    # above `oversold` and not yet crossed back down through `overbought`
    # after having reached it (classic oversold-recovery -> overbought-exit
    # cycle capture).
    weekly_position = pd.Series(0, index=weekly_rsi.index, dtype=int)
    in_pos = False
    was_overbought = False
    for i in range(len(weekly_rsi)):
        r = weekly_rsi.iloc[i]
        if pd.isna(r):
            weekly_position.iloc[i] = 1 if in_pos else 0
            continue
        if not in_pos:
            prev = weekly_rsi.iloc[i - 1] if i > 0 else None
            if prev is not None and not pd.isna(prev) and prev <= oversold and r > oversold:
                in_pos = True
                was_overbought = False
        else:
            if r >= overbought:
                was_overbought = True
            if was_overbought and r < overbought:
                in_pos = False
        weekly_position.iloc[i] = 1 if in_pos else 0

    # Forward-fill weekly decisions onto daily index (signal known as of
    # each week's close, applied going forward until the next weekly close).
    daily_position = weekly_position.reindex(df.index, method="ffill").fillna(0).astype(int)
    return daily_position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
