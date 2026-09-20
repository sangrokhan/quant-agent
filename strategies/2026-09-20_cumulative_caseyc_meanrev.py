"""Strategy: Cumulative CaseyC% Mean Reversion (3-bar summed momentum percentile).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-134):
Per Ali Casey's CaseyC% oscillator (StatOasis,
https://statoasis.com/overfit/research/caseyc-oscillator-a-smarter-mean-reversion-strategy-for-sp500-traders,
visited via browser_exec this iteration): CaseyC% ranks N-period momentum
(ChangeLen, i.e. an ROC-style price-change) within a trailing RankLen
window via percentile rank, scaled 0-100, then smoothed. This base
construction is close to this repo's already-accepted Cesar Alvarez
PercentRank(ROC) strategy (id=2026-09-04-121: PercentRank of ROC(2) over a
252-day window). The source's own stated improvement over its "Regular
CaseyC%" variant, however, is "Cumulative CaseyC%" -- summing the last 3
daily CaseyC% readings into a single value before thresholding, explicitly
described as "a stronger mean reversion filter that smooths out noisy
signals" -- which is a genuinely different signal-smoothing mechanic
(temporal summation of percentile ranks, not a smoothing moving-average
applied to the ROC or a longer PercentRank lookback) not previously tested
in this repo. This iteration tests specifically the Cumulative variant
to isolate whether temporal summation of oscillator readings (rather than
just a single day's extreme reading) provides an edge that the plain
2026-09-04-121 construction did not have on SPY/crypto.

Signal logic
------------
- roc = ROC(close, change_len) (percent price change over change_len bars).
- percentile_rank[t] = percentile rank of roc[t] within its own trailing
  rank_len-bar history, scaled to [0, 100] (0 = lowest ROC in the window,
  100 = highest).
- cumulative_c = rolling sum of the last cum_window daily percentile_rank
  values.
- Entry (long): cumulative_c crosses below entry_threshold (a persistent
  multi-day run of low-percentile-rank readings, not just one extreme day),
  optionally gated by close > SMA(trend_window) (uptrend filter, following
  this repo's established pattern for oversold-dip mean-reversion entries).
- Exit: cumulative_c crosses back above exit_threshold OR max_hold_days
  time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _percentile_rank(series: pd.Series, window: int) -> pd.Series:
    def _rank_last(x):
        if len(x) < 2:
            return float("nan")
        last = x[-1]
        return (x < last).sum() / (len(x) - 1) * 100.0

    return series.rolling(window).apply(_rank_last, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    change_len: int = 2,
    rank_len: int = 100,
    cum_window: int = 3,
    entry_threshold: float = 30.0,
    exit_threshold: float = 150.0,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    roc = close.pct_change(change_len) * 100.0
    percentile_rank = _percentile_rank(roc, rank_len)
    cumulative_c = percentile_rank.rolling(cum_window).sum()

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    entry_cross = (cumulative_c < entry_threshold) & (cumulative_c.shift(1) >= entry_threshold) & uptrend.fillna(False)
    exit_cross = (cumulative_c > exit_threshold) & (cumulative_c.shift(1) <= exit_threshold)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_cross.iloc[i]):
                in_position = True
                entry_idx = i
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
