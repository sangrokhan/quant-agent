"""Strategy: N-bar New High + Low Internal Bar Strength (IBS) breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-019):
Per QuantifiedStrategies.com's "Buy When S&P 500 Makes New Intraday High"
(reproduced/tested at
https://www.prorealcode.com/topic/buy-when-sp500-makes-new-high-and-ibs-is-low-strategy/,
browser_exec, free/fully disclosed rule since the original QS article page
404'd but its exact rules are quoted verbatim by the forum author): a long
entry triggers when today's HIGH exceeds the highest high of the prior
lookback_p-1 bars (a new short-term high -- strength) AND today's Internal
Bar Strength IBS=(close-low)/(high-low) is BELOW ibs_threshold (the bar
closed weak relative to its own range -- an intrabar pullback within an
otherwise strong bar). This combines a breakout condition with an
intrabar-weakness confirmation, the opposite combination of every other IBS
strategy in this repo (which use LOW IBS alone, or IBS alongside a
mean-reversion/oversold context, never alongside a fresh N-bar HIGH
breakout). Exit when close > yesterday's high (source's own rule) or after
a max_hold_days safety time-stop (source has none; added here to bound
tail-risk holds since this is a swing-length position, not the fixed-N
overnight-only holds like our other IBS strategies).

Source's own author-run sweep found p~5 and ibs_threshold in the 0.15-0.19
region gave the best avg-gain/win-rate trade-off on SPX; p=2 maximizes trade
count. This iteration tests p in {2, 5, 10} x ibs_threshold in {0.15, 0.20,
0.25}.

Interface contract:
    generate_signals(price_df, **params) -> pd.Series ({0,1})
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
    lookback_p: int = 5,
    ibs_threshold: float = 0.15,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    prior_highest_high = high.shift(1).rolling(lookback_p - 1 if lookback_p > 1 else 1).max()
    new_high = high > prior_highest_high

    rng = (high - low).replace(0.0, pd.NA)
    ibs = (close - low) / rng
    low_ibs = ibs < ibs_threshold

    entry_signal = (new_high & low_ibs).fillna(False)

    prior_high = high.shift(1)
    exit_target_signal = close > prior_high

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = -1
    idx_list = df.index

    for i in range(len(idx_list)):
        if not in_position:
            if bool(entry_signal.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
        else:
            held_days = i - entry_idx
            if bool(exit_target_signal.iloc[i]) or held_days >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
