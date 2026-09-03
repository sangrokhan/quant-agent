"""Strategy: Bollinger Band lower-touch + RSI oversold confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-067):
Per FXGlory's Bollinger Bands + RSI combination guide: a lower Bollinger
Band touch (close < lower band) combined with RSI oversold (RSI < 30)
suggests a stretched-price/weak-momentum reversal candidate worth
reviewing. Distinct from this repo's prior BB mean-reversion attempts
(2026-09-03-001 vol-regime gated, 2026-09-03-023 ATR-percentile+slope
dual-gated) since this adds an RSI-oversold CONFIRMATION filter rather
than a volatility/slope regime gate. Long entry when close < lower BB AND
RSI < 30; exit when close crosses back above the middle SMA band OR RSI
rises above 70 (overbought).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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
    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-12)
    return 100 - (100 / (1 + rs))


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    rsi_window: int = 14,
    rsi_oversold: float = 30.0,
    rsi_overbought: float = 70.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    lower_band = sma - bb_std * std

    rsi = _rsi(close, rsi_window)

    entry_signal = (close < lower_band) & (rsi < rsi_oversold)
    exit_signal = (close >= sma) | (rsi > rsi_overbought)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
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
