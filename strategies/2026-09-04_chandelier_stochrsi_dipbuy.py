"""Strategy: Chandelier Exit trailing stop + StochRSI oversold-recovery entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-035):
Per StockCharts ChartSchool's Chandelier Exit article (Charles Le Beau /
Alexander Elder): the Chandelier Exit (a volatility-adaptive trailing stop,
period-high minus a multiple of ATR) defines the trend/risk boundary, and
should be paired with a separate momentum oscillator to time entries within
the established uptrend rather than used as an entry signal itself. The
source's own worked example: StochRSI dipping below 0.20 (short-term
oversold) then recovering back above 0.20 signals a good dip-buy entry
*while price remains above the Chandelier long-stop line* (i.e. the broader
uptrend is intact). This differs from the prior chandelier-exit strategy
tested in this repo (2026-09-04-025, all-time-high breakout entry) by using
a pullback/dip-buy entry mechanism instead of a fresh-high breakout entry,
while reusing the same trailing-stop exit mechanic.

Chandelier Exit formula (source, standard params: 22-period, ATR multiplier 3):
    chandelier_long = rolling_max(high, window) - ATR(window) * multiplier

StochRSI formula (Stochastic Oscillator applied to RSI, standard params:
rsi_window=14, stoch_window=14): compute RSI(rsi_window), then apply the
%K stochastic formula to the RSI series over stoch_window, scaled 0-1.

Signal logic
------------
- Trend/risk boundary: close > chandelier_long (i.e. above the trailing
  stop line -- an uptrend is in force).
- Entry (long): StochRSI crosses from <= oversold_threshold (0.20) back
  above it (fresh recovery, not every bar StochRSI stays low) AND
  close > chandelier_long at that moment.
- Exit: close crosses below chandelier_long (the trailing stop is hit).
- Flat otherwise; long-only, no shorting.

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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50.0)
    return rsi


def _stoch_rsi(close: pd.Series, rsi_window: int, stoch_window: int) -> pd.Series:
    rsi = _rsi(close, rsi_window)
    lowest = rsi.rolling(stoch_window).min()
    highest = rsi.rolling(stoch_window).max()
    denom = (highest - lowest).replace(0.0, pd.NA)
    stoch_rsi = (rsi - lowest) / denom
    return stoch_rsi.fillna(0.5)


def generate_signals(
    price_df: pd.DataFrame,
    chandelier_window: int = 22,
    atr_multiplier: float = 3.0,
    rsi_window: int = 14,
    stoch_window: int = 14,
    oversold_threshold: float = 0.20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    atr = _atr(df, chandelier_window)
    chandelier_long = high.rolling(chandelier_window).max() - atr * atr_multiplier

    stoch_rsi = _stoch_rsi(close, rsi_window, stoch_window)
    recovery_cross = (stoch_rsi > oversold_threshold) & (stoch_rsi.shift(1) <= oversold_threshold)

    uptrend = close > chandelier_long
    entry = recovery_cross & uptrend.fillna(False)
    exit_signal = close < chandelier_long

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
