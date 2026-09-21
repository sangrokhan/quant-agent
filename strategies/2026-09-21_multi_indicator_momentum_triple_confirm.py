"""Strategy: Multi-Indicator Momentum (RSI + Stochastic %K + Williams %R
triple-confirmation, gated by a short-term prior-return filter).

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per StatOasis's "Can AI Build a Profitable Trading Strategy?" study
(https://statoasis.com/overfit/research/ai-strategy-validation, read via
browser_exec -- web_search DDGS backend was TLS-erroring on multiple
queries this iteration), one of 5 LLM-generated mechanical rule-sets
tested on SPY out-of-sample (2016-2026) was the strongest performer and
the only one to clear a 95th-percentile Monte Carlo significance screen
(percentile 96.7, i.e. random entries matched/beat it only 3.3% of the
time): "Rule 4: Multi-Indicator Momentum -- RSI(14)>55 AND Stochastic
%K(14)>50 AND Williams %R(14)>-50 AND 5-day prior return>1%, long, 10-bar
hold." The source's own verdict was nuanced (even this rule lost to
buy-and-hold on raw net profit over the OOS window, though it beat random
timing with high statistical confidence) -- this iteration tests it
directly against this repo's own Sharpe/MDD/TC/walk-forward/param-
sensitivity validator suite rather than the source's OOS-vs-buy-and-hold /
Monte-Carlo framework, to see if it clears THIS repo's bar.

First strategy in this repo requiring RSI + Stochastic %K + Williams %R
to ALL simultaneously confirm bullish momentum (each in isolation is
already tested extensively as a mean-reversion oscillator-threshold entry
elsewhere in this repo, but never combined as a triple-AND momentum
CONTINUATION confirmation gated by a raw N-day price-return filter).

Signal logic
------------
- RSI(rsi_window) > rsi_threshold (momentum confirmation, source: >55).
- Stochastic %K(stoch_window) > stoch_threshold (source: >50).
- Williams %R(wr_window) > wr_threshold (source: >-50; Williams %R ranges
  [-100, 0], so ">-50" means the close is in the upper half of its recent
  high-low range).
- 5-day prior return (close today vs close return_window days ago) >
  return_threshold (source: >1%).
- Entry: all four conditions true simultaneously -> go long at that bar's
  close.
- Exit: fixed hold_days-bar time exit (source's own disclosed rule -- no
  signal-based exit specified).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _stoch_k(df: pd.DataFrame, window: int) -> pd.Series:
    low_min = df["low"].rolling(window).min()
    high_max = df["high"].rolling(window).max()
    rng = (high_max - low_min).replace(0, pd.NA)
    k = 100 * (df["close"] - low_min) / rng
    return k


def _williams_r(df: pd.DataFrame, window: int) -> pd.Series:
    high_max = df["high"].rolling(window).max()
    low_min = df["low"].rolling(window).min()
    rng = (high_max - low_min).replace(0, pd.NA)
    wr = -100 * (high_max - df["close"]) / rng
    return wr


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    rsi_threshold: float = 55.0,
    stoch_window: int = 14,
    stoch_threshold: float = 50.0,
    wr_window: int = 14,
    wr_threshold: float = -50.0,
    return_window: int = 5,
    return_threshold: float = 0.01,
    hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_window)
    stoch_k = _stoch_k(df, stoch_window)
    wr = _williams_r(df, wr_window)
    prior_ret = close.pct_change(return_window)

    entry = (
        (rsi > rsi_threshold)
        & (stoch_k > stoch_threshold)
        & (wr > wr_threshold)
        & (prior_ret > return_threshold)
    ).fillna(False)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if held >= hold_days:
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
    strategy_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strategy_ret
