"""Strategy: RSI(5) 30-50 Pullback (QuantifiedStrategies "RSI 30 50 for Beginners").

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-014):
Per QuantifiedStrategies.com's "RSI 30 50 Strategy for Beginners"
(https://quantifiedstrategies.substack.com/p/rsi-30-50-strategy-for-beginners,
free, fully disclosed rule): in a bullish market (price above a rising
200-day SMA), the 30-50 RSI zone marks a PULLBACK (not a reversal) worth
buying. Rule (source's own): only trade in a confirmed uptrend
(close>SMA(200)); wait for a 5-day-lookback RSI to drop below 30 (long
entry trigger); sell when RSI recovers to >=50. Source's own S&P 500
backtest: 196 trades, 0.9% avg gain/trade, 81% win rate, profit factor 3,
CAGR 5.3%, only 11% time-in-market (risk-adjusted return 44% = CAGR/exposure),
MDD -15%.

Distinct from every other RSI(2)-family entry in this repo (45+ prior
hits): this uses RSI(5) specifically (not RSI(2)/RSI(3)), a 30-threshold
entry (not <5/<10), and a fixed 50-threshold exit (not a 5-day-SMA cross
or prior-day-high exit) -- the specific 5-period/30-in/50-out combination
has 0 prior hits in this repo's index.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 5,
    entry_threshold: float = 30.0,
    exit_threshold: float = 50.0,
    trend_ma_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_window)
    trend_ok = close > close.rolling(trend_ma_window).mean()

    entry = (rsi < entry_threshold) & trend_ok
    exit_signal = rsi >= exit_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
