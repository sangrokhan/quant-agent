"""Strategy: GLD/SLV ratio RSI(5) pairs-trade-style long-GLD momentum.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-047):
Per quantifiedstrategies.com's Gold/Silver Chart Ratio Strategy article
(visited this iteration, https://www.quantifiedstrategies.com/gold-silver-chart-ratio-strategy/):
the source's own disclosed pairs-trade rule is a direct GLD/SLV pairs
trade using a 5-day RSI of the ratio: buy GLD (and short SLV) when the
5-day RSI of the GLD/SLV ratio closes above 75 (gold rapidly strengthening
vs silver -- "the gold-silver ratio has been one of the most reliable
technical indicators for a buy signal in silver whenever the ratio climbs
above 80"), exit when RSI falls back below 50. The source explicitly
reports its own pair-trade equity curve "shows a flat development" (a
weak/unremarkable result by the source's own admission) -- worth testing
independently rather than assuming failure.

This repo approximates GLD/SLV as a single-leg long-only GLD trade (no
short SLV leg), consistent with the repo's convention for other pairs-trade
adaptations (ETH/BTC id=2026-09-04-083, JPM/BAC id=2026-09-08-071, GDX/RING
id=2026-09-10-023). Distinct from this repo's existing GLD/SLV ratio
z-score REGIME GATE (2026-09-05-030), which uses the ratio to gate a
DIFFERENT primary asset's long/flat signal rather than trading GLD/SLV
directly via an RSI-of-the-ratio momentum trigger.

Signal logic
------------
- ratio = GLD.close / SLV.close (supplied externally as a pd.DataFrame
  with a `ratio` column, pre-aligned to price_df's index by the caller).
- ratio_rsi = Wilder's RSI(rsi_window) applied to the ratio series
  (default rsi_window=5, per source's own "5-day RSI").
- Entry (long GLD): ratio_rsi crosses above entry_threshold (default 75).
- Exit: ratio_rsi falls below exit_threshold (default 50), or a
  max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both require a `ratio_df` kwarg: a pd.DataFrame with a DatetimeIndex and a
`ratio` column (GLD/SLV), pre-aligned to price_df's asset by the caller.
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


def _ratio_rsi_aligned(index: pd.DatetimeIndex, ratio_df: pd.DataFrame, rsi_window: int) -> pd.Series:
    rdf = ratio_df.copy()
    target_index = index
    if getattr(target_index, "tz", None) is not None:
        target_index = target_index.tz_localize(None)
    if getattr(rdf.index, "tz", None) is not None:
        rdf.index = rdf.index.tz_localize(None)

    ratio = rdf["ratio"].sort_index()
    rsi = _wilder_rsi(ratio, rsi_window)
    rsi_aligned = rsi.reindex(target_index.union(rsi.index)).sort_index().ffill().reindex(target_index)
    rsi_aligned.index = index
    return rsi_aligned


def generate_signals(
    price_df: pd.DataFrame,
    ratio_df: pd.DataFrame,
    rsi_window: int = 5,
    entry_threshold: float = 75.0,
    exit_threshold: float = 50.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ratio_rsi = _ratio_rsi_aligned(df.index, ratio_df, rsi_window)

    entry_cross = (ratio_rsi > entry_threshold) & ~(ratio_rsi.shift(1) > entry_threshold).fillna(False)
    exit_cond = ratio_rsi < exit_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cond.iloc[i]) or held >= max_hold_days:
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
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
