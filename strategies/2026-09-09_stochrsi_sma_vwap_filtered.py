"""Strategy: Stochastic RSI crossover with SMA-spread and VWAP filters (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-103):
Per TradingView's "Stochastic RSI Strategy (with SMA and VWAP Filters)"
by thedoggwalker (fully disclosed rule set): long entry when the
Stochastic RSI crosses above 30 (exiting oversold), gated by (1) a
positive spread between a 9-period SMA and a 21-period SMA (short-term
momentum confirms uptrend) and (2) close being BELOW the volume-weighted
average price (source's own stated condition -- pulling back to value
before the reversal, a mean-reversion-flavored filter layered on a
momentum trigger). Source's exact risk management: fixed-tick stop-loss
and take-profit (20/25 ticks); adapted here to a percentage-based
stop/target since this repo's assets don't share tick sizes, plus a
max_hold_days time-stop backstop.

First Stochastic RSI (%K stochastic-of-RSI, distinct from plain RSI or
Stochastic Oscillator alone) strategy in this repo (0 prior hits on
"Stochastic RSI Crossover") -- this repo has tested plain Stochastic
Oscillator and plain RSI separately, but not the STOCH(RSI) composite
oscillator combined with a dual-SMA-spread trend filter AND a
VWAP-relative-position filter simultaneously.

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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss.replace(0.0, float("nan"))
    rsi = 100 - 100 / (1 + rs)
    rsi = rsi.where(avg_loss != 0, 100.0)
    rsi = rsi.where(~((avg_loss == 0) & (avg_gain == 0)), 50.0)
    return rsi.astype(float)


def _stoch_rsi(close: pd.Series, rsi_window: int, stoch_window: int) -> pd.Series:
    rsi = _rsi(close, rsi_window)
    rsi_min = rsi.rolling(stoch_window).min()
    rsi_max = rsi.rolling(stoch_window).max()
    denom = (rsi_max - rsi_min).replace(0.0, float("nan"))
    stoch_rsi = (rsi - rsi_min) / denom * 100
    return stoch_rsi.fillna(50.0)


def _vwap_since_anchor(df: pd.DataFrame, window: int) -> pd.Series:
    """Rolling-window VWAP proxy (typical price weighted by volume)."""
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    pv = typical_price * df["volume"]
    return pv.rolling(window).sum() / df["volume"].rolling(window).sum()


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    stoch_window: int = 14,
    fast_sma: int = 9,
    slow_sma: int = 21,
    vwap_window: int = 20,
    stop_pct: float = 0.03,
    target_pct: float = 0.0375,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    stoch_rsi = _stoch_rsi(close, rsi_window, stoch_window)
    fast_ma = close.rolling(fast_sma).mean()
    slow_ma = close.rolling(slow_sma).mean()
    vwap = _vwap_since_anchor(df, vwap_window)

    above_30 = stoch_rsi > 30
    cross_above_30 = above_30 & (~above_30.shift(1).fillna(False))
    positive_spread = fast_ma > slow_ma
    below_vwap = close < vwap

    entry = cross_above_30 & positive_spread.fillna(False) & below_vwap.fillna(False)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = None

    for i in range(n):
        if in_position:
            held = i - entry_idx
            stop_hit = entry_price is not None and close.iloc[i] < entry_price * (1 - stop_pct)
            target_hit = entry_price is not None and close.iloc[i] > entry_price * (1 + target_pct)
            if stop_hit or target_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                entry_price = None
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                entry_price = close.iloc[i]
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
