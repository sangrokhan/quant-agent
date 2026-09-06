"""Strategy: RSI Range-Momentum (RSI used as a momentum, not mean-reversion,
indicator).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-184):
Most RSI strategies treat it as an oscillator for mean reversion (buy
oversold <30, sell overbought >70) -- this repo has already tested many
such variants. Per Arthur Hill's "Finding consistent trends with strong
momentum" (as summarized by QuantifiedStrategies.com's RSI Range-Momentum
article), RSI's TRUE nature is a momentum indicator: during an uptrend RSI
typically ranges 40-80 and finds support in the 40-50 zone on pullbacks,
while during a downtrend it ranges 20-60. This strategy operationalizes
that observation into two boolean conditions computed over a rolling
lookback window:
  - RSI Bull Range: RSI has stayed within [40, 100] for the entire lookback
    window (no oversold breaks below 40 -- i.e. no genuine downtrend
    behavior recently).
  - RSI Bull Momentum: the MAX RSI value over the lookback window exceeded
    70 (confirms actual bullish momentum occurred, not just flat drift).
Entry: long when BOTH conditions are true. Exit: only when BOTH conditions
become false simultaneously (the source's own "asymmetric" persistence
rule -- if only one condition flips false while the other stays true, stay
in the position). Per the source's own SPY backtest (1993-present): CAGR
5.93% vs buy-hold 9.58%, only 35.7% time in market, 12 total trades, 83%
win rate, MDD 12.9% -- a low-frequency, high-win-rate, low-drawdown
uptrend-persistence filter rather than a signal generator. First RSI-as-
momentum (as opposed to RSI-as-mean-reversion-oscillator) strategy in this
repo.
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
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    lookback_window: int = 100,
    bull_range_low: float = 40.0,
    bull_momentum_threshold: float = 70.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_window)

    rsi_bull_range = (rsi.rolling(lookback_window).min() >= bull_range_low)
    rsi_bull_momentum = (rsi.rolling(lookback_window).max() > bull_momentum_threshold)

    entry_ok = (rsi_bull_range & rsi_bull_momentum).fillna(False)
    exit_ok = (~rsi_bull_range & ~rsi_bull_momentum).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_ok.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_ok.iloc[i]):
                in_position = True
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
