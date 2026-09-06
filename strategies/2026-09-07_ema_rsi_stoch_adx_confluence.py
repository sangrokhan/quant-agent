"""Strategy: 4-indicator momentum-continuation AND-gate (34/89 EMA trend +
fast 3-period RSI extreme + Stochastic-above-signal + ADX +DI confirmation).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-024):
Per a widely-circulated Forex-education "EMA + RSI Trading Plan" rule set
(disclosed identically across multiple Facebook trading-education posts,
e.g. AsiaForexMentor.com's "exact setup" reel and a Course Hero-hosted
"Trading strategies collection.pdf"; the rule is quoted verbatim across
>=3 independent sources so treated as a genuine, reproducible mechanical
rule despite the informal distribution channel): a long entry requires
FOUR simultaneous conditions to agree that a strong bullish trend is both
established AND currently accelerating:
  1. 34-period EMA > 89-period EMA (Fibonacci-period EMA pair, a slower
     trend-alignment filter than any single EMA/SMA trend filter already
     tested in this repo).
  2. A fast 3-period RSI crosses above 80 (an unusually high oversold-free
     "momentum thrust" trigger -- 3-period RSI is far noisier/faster than
     the repo's existing RSI(2)/RSI(14) variants, and 80 is a MOMENTUM
     confirmation level here, not an overbought exhaustion signal, since
     the source's own framing is "spot high-probability entries" during
     trend continuation, not mean reversion).
  3. Stochastic %K is above its own %D signal line (standard bullish
     stochastic-crossover state, not a fresh cross -- a persistence
     condition).
  4. ADX's +DI line is above its -DI line (directional confirmation that
     the EMA "uptrend" per condition 1 also has current bullish directional
     dominance, not just historical price-level ordering).
Exit: mirror-reverse of the entry gate (any one condition flipping against
the position), or a max_hold_days time-stop backstop (source specifies no
explicit stop).

This 4-way simultaneous-AND-gate combining a slow EMA trend filter, a
fast RSI extreme-momentum trigger, a Stochastic persistence state, AND an
ADX directional-dominance filter is distinct from every prior combo
strategy in this repo (e.g. TDI id=2026-09-04-117 combines RSI+Bollinger
only; RSI+MACD id=2026-09-04-161 combines only 2 conditions; Vortex+ADX
id=2026-09-06-091 combines only 2) via requiring FOUR independently-
sourced confirmations to align simultaneously.

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


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _stochastic(df: pd.DataFrame, k_window: int = 14, d_window: int = 3) -> tuple[pd.Series, pd.Series]:
    low_min = df["low"].rolling(k_window).min()
    high_max = df["high"].rolling(k_window).max()
    denom = (high_max - low_min).replace(0, pd.NA)
    k = 100 * (df["close"] - low_min) / denom
    k = k.fillna(50.0)
    d = k.rolling(d_window).mean()
    return k, d


def _adx_di(df: pd.DataFrame, window: int = 14) -> tuple[pd.Series, pd.Series]:
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = ((up_move > down_move) & (up_move > 0)).astype(float) * up_move.clip(lower=0)
    minus_dm = ((down_move > up_move) & (down_move > 0)).astype(float) * down_move.clip(lower=0)

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean() / atr.replace(0, pd.NA)
    minus_di = 100 * minus_dm.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean() / atr.replace(0, pd.NA)
    return plus_di.fillna(0.0), minus_di.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    ema_fast: int = 34,
    ema_slow: int = 89,
    rsi_window: int = 3,
    rsi_thresh: float = 80.0,
    stoch_k_window: int = 14,
    stoch_d_window: int = 3,
    adx_window: int = 14,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema_f = _ema(close, ema_fast)
    ema_s = _ema(close, ema_slow)
    trend_up = ema_f > ema_s

    rsi = _rsi(close, rsi_window)
    rsi_momentum = rsi > rsi_thresh

    stoch_k, stoch_d = _stochastic(df, stoch_k_window, stoch_d_window)
    stoch_bullish = stoch_k > stoch_d

    plus_di, minus_di = _adx_di(df, adx_window)
    di_bullish = plus_di > minus_di

    entry_ok = (
        trend_up.fillna(False)
        & rsi_momentum.fillna(False)
        & stoch_bullish.fillna(False)
        & di_bullish.fillna(False)
    )
    exit_signal = ~(trend_up.fillna(False) & stoch_bullish.fillna(False) & di_bullish.fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_count = 0
    for i in range(len(close)):
        if in_position:
            hold_count += 1
            if bool(exit_signal.iloc[i]) or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_ok.iloc[i]):
                in_position = True
                hold_count = 0
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
