"""Strategy: Kairi Relative Index (KRI) mean-reversion pullback, trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-167):
The Kairi Relative Index (Japanese-origin oscillator = 100 * (close - SMA) /
SMA, a percentage-deviation-from-mean measure) dropping to/below an oversold
threshold (source's default -10%, tested here as a tunable parameter) marks
a short-term mean-reversion long entry, but ONLY when the broader trend is
up (close > long-term SMA(200) trend filter) -- per quantifiedstrategies.com's
own article, which explicitly warns that in a strong downtrend KRI can stay
oversold for a long time without reverting, so a trend gate is needed to
avoid catching falling knives. Exit when KRI recovers back above an exit
threshold (near/above zero) or a max_hold_days time-stop backstop.

Source: https://www.quantifiedstrategies.com/kairi-relative-index/
(full numeric backtest rules paywalled; KRI formula, +/-10% overbought/
oversold levels, SMA-period>20 guidance, and the trend-direction caveat are
all disclosed in the free portion of the article).

First Kairi Relative Index strategy tested in this repo -- distinct from
other price-vs-moving-average deviation measures already tested (Z-Score
id 2026-09-03-xxx uses std-normalized deviation, not simple pct deviation;
DPO id 2026-09-04-056 uses a backward-shifted SMA baseline and trades
zero-crossings, not oversold-threshold-and-recovery).

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


def _kairi(close: pd.Series, sma_window: int) -> pd.Series:
    sma = close.rolling(sma_window).mean()
    return 100.0 * (close - sma) / sma


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 26,
    entry_threshold: float = -10.0,
    exit_threshold: float = 0.0,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    kri = _kairi(close, sma_window)
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    entry = (kri <= entry_threshold) & uptrend.fillna(False)
    exit_recover = kri >= exit_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_recover.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
