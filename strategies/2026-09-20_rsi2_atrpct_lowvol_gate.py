"""Strategy: Connors RSI(2) mean reversion, gated by a low-volatility ATR%
regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-140):
Per Ali Casey's StatOasis article "Do Volume and Volatility Filters Actually
Improve RSI(2)? 15,552 Backtests Say Mostly No"
(https://statoasis.com/overfit/research/boost-your-rsi2-strategy-for-sp500-by-48-with-this-volume-filter,
visited via browser_exec this iteration): out of 80 volume/volatility
filters bolted onto Larry Connors' plain RSI(2) mean-reversion strategy
(long when 2-period RSI closes below a lower threshold, exit when it
closes back above an upper threshold), the ONE filter that consistently
helped was a volatility filter, not a volume filter: gating entries to
only fire when ATR% (ATR(atr_window)/close) is below its own trailing
atr_lookback-day rolling median. This improved profit factor in 75.0% of
96 matched pairings and cut worst drawdown by 5.6 percentage points, while
still letting through 50.8% of signals (much higher signal-retention than
any volume filter tested, which kept <20% of signals for a comparable
profit-factor gain). This is the source's own explicitly-measured single
best filter out of an 80-filter sweep, distinct from every prior
RSI(2)/Connors-RSI entry in this repo's saturated RSI(2) family (12+ prior
entries per 2026-09-10-005's own count) because none of them specifically
test this exact ATR%-below-own-trailing-median volatility gate on top of
plain RSI(2) mean reversion.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _wilder_rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, min_periods=length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()


def generate_signals(
    price_df: pd.DataFrame,
    rsi_len: int = 2,
    entry_threshold: float = 10.0,
    exit_threshold: float = 70.0,
    atr_window: int = 14,
    atr_lookback: int = 100,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _wilder_rsi(close, rsi_len)
    atr = _atr(df, atr_window)
    atr_pct = atr / close
    atr_pct_median = atr_pct.rolling(atr_lookback).median()
    low_vol_regime = atr_pct <= atr_pct_median

    entry = (rsi < entry_threshold) & low_vol_regime.fillna(False)
    exit_meanrev = rsi > exit_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
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
