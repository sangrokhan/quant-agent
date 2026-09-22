"""Strategy: Percentile Channel trend-following with hysteresis (Varadi-style).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-042):
Per David Varadi's CSSA blog post "A Simple Tactical Asset Allocation
Portfolio with Percentile Channels" (https://cssanalytics.wordpress.com/2015/
01/26/a-simple-tactical-asset-allocation-portfolio-with-percentile-channels/,
read via browser_exec since web_extract's DDGS backend cannot fetch article
bodies), the disclosed mechanical rule is: compute the rolling percentile
rank of the current close within its own trailing N-day window (a
"percentile channel", N in {60,120,180,252} corresponding to ~3/6/9/12
calendar months); go long when that percentile rank crosses above 0.75
(strong uptrend), hold until it crosses back below 0.25 (hysteresis band
avoids whipsaw), then exit/flat. Source's own reported multi-asset TAA
portfolio using this signal achieved Sharpe near 2.0 with low max drawdown.

This is a genuinely distinct mechanical construction for this repo: prior
percentile-rank entries in this KB rank a *derived* series (ATR, Bollinger
Band width, ROC/momentum, CSI, MMI-median-deviation) rather than the raw
CLOSE PRICE ITSELF, and none use this specific asymmetric 0.75-entry /
0.25-exit hysteresis band -- most prior percentile-rank strategies use a
single crossing threshold with no separate entry/exit levels. Adapted
single-asset (source used a 4-asset diversified TAA basket + risk-parity
sizing across assets; here tested as a single-symbol long/flat channel
signal, matching this repo's other single-asset-adaptation convention).

Signal logic
------------
- pct_rank_t = fraction of the trailing `window` daily closes (inclusive)
  that are <= close_t (i.e. close's own percentile rank in its recent
  history).
- Long (1) when pct_rank crosses above entry_threshold (0.75) and stays
  long until pct_rank drops below exit_threshold (0.25); flat (0)
  otherwise. This produces exactly the source's stated hysteresis logic.
- Evaluated once per rebalance_days trading days (source rebalances
  monthly), matching the TAA-style monthly-tranche cadence.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  (0/1 position series)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _pct_rank(close: pd.Series, window: int) -> pd.Series:
    # causal rolling percentile rank of the current close within its own
    # trailing `window` observations (inclusive of the current bar).
    def rank_last(x):
        return (x <= x[-1]).sum() / len(x)

    return close.rolling(window).apply(rank_last, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 126,
    entry_threshold: float = 0.75,
    exit_threshold: float = 0.25,
    rebalance_days: int = 21,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    pct_rank = _pct_rank(close, window)

    n = len(df)
    positions = pd.Series(0, index=df.index, dtype=int)
    held = 0

    for i in range(n):
        if i % rebalance_days == 0:
            r = pct_rank.iloc[i]
            if pd.notna(r):
                if held == 0 and r > entry_threshold:
                    held = 1
                elif held == 1 and r < exit_threshold:
                    held = 0
        positions.iloc[i] = held

    positions.iloc[: window] = 0
    return positions.fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    window: int = 126,
    entry_threshold: float = 0.75,
    exit_threshold: float = 0.25,
    rebalance_days: int = 21,
) -> pd.Series:
    df = _prep(price_df)
    positions = generate_signals(
        df,
        window=window,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        rebalance_days=rebalance_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = positions.shift(1).fillna(0) * daily_ret
    return strat_ret
