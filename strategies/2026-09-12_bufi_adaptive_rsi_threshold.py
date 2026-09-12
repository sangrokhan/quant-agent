"""Strategy: Bufi Adaptive Oscillator Threshold (BAT) applied to RSI(2), long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Francesco Bufi's "Overbought/Oversold Oscillators: Useless Or Just
Misused" (TASC Traders' Tips, October 2024; fully disclosed Pine v5 source at
https://www.tradingview.com/script/zDP76aFT-TASC-2024-10-Adaptive-Oscillator-Threshold/),
a static oscillator buy-threshold (e.g. "RSI < 14") ignores trend direction
and volatility. Bufi's Adaptive Threshold (BAT) rescales the buy level by a
factor proportional to a rolling linear-regression slope (trend) and
inversely proportional to rolling stdev (dispersion), clamped to [-0.5, 0.5]:

    BAT(price, length) = clip(slope / stdev(price, length), -0.5, 0.5)
    slope = (linreg(price, length, 0) - price[length]) / (length + 1)

The adaptive buy threshold is `buy_level * adap_k * BAT(close, adap_len)`.
Entry (long): RSI(rsi_len) crosses/is below this adaptive threshold (a
DEEPER pullback is required in a downtrend since a negative slope drives
the threshold negative, and a shallower pullback suffices during a strong
uptrend with low dispersion, since threshold rises toward buy_level).
Exit: fixed-bar time-stop after `exit_bars` bars (the source's own primary
exit rule; its "dollar stop-loss" is a fixed-notional stop that doesn't
port cleanly to a percentage-return framework and is intentionally omitted
here, noted as a scope limitation).

This is the first Bufi/BAT-family adaptive-threshold strategy in this repo,
distinct from all prior RSI-threshold variants (e.g. plain RSI(2) mean
reversion, HHLLS, TRAdj EMA) because the threshold itself is TIME-VARYING as
a function of trend+dispersion rather than fixed or itself an oscillator.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    # Wilder's smoothing (matches Pine's ta.rsi)
    avg_gain = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0, 100.0)
    return rsi


def _linreg_endpoint(series: pd.Series, length: int) -> pd.Series:
    """Rolling OLS fit value at the LAST point of each window (Pine ta.linreg(x, length, 0))."""
    x = np.arange(length, dtype=float)
    x_mean = x.mean()
    denom = ((x - x_mean) ** 2).sum()

    def _fit_last(window: np.ndarray) -> float:
        y_mean = window.mean()
        slope = ((x - x_mean) * (window - y_mean)).sum() / denom
        intercept = y_mean - slope * x_mean
        return intercept + slope * x[-1]

    return series.rolling(length).apply(_fit_last, raw=True)


def _bat(close: pd.Series, length: int) -> pd.Series:
    sd = close.rolling(length).std(ddof=0)
    lr = _linreg_endpoint(close, length)
    price_lag = close.shift(length)
    slope = (lr - price_lag) / (length + 1)
    bat = (slope / sd.replace(0.0, np.nan)).clip(-0.5, 0.5)
    return bat


def generate_signals(
    price_df: pd.DataFrame,
    rsi_len: int = 2,
    buy_level: int = 14,
    adap_len: int = 8,
    adap_k: float = 6.0,
    exit_bars: int = 28,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    osc = _rsi(close, rsi_len)
    bat = _bat(close, adap_len)
    thrs = buy_level * adap_k * bat

    entry = (osc < thrs) & thrs.notna() & osc.notna()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= exit_bars:
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
