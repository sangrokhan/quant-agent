"""Strategy: Gopalakrishnan Range Index (GAPO) Low-Volatility Mean Reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-010):
Per technicalresources.in's "Comprehensive Guide to Trading Strategies Using
Gopalakrishnan Range Index (GAPO)" (Tushar Chande's fractal-dimension-style
volatility index, 0-1 range; low values = smooth/low-vol, high values =
complex/high-vol): source's own "Strategy 2: Mean Reversion Strategy in Low
Volatility Markets" states "Low GAPO values (below 0.3) indicate stability,
which favors mean-reversion strategies... Combine GAPO with oscillators like
RSI or Stochastic to identify overbought/oversold conditions. Enter trades
when the price deviates significantly from the mean (e.g., moving averages).
Exit when the price returns to the mean."

Mechanized here as: GAPO(gapo_window) < gapo_threshold (low-vol regime) AND
RSI(rsi_window) <= rsi_oversold (oversold) triggers a long entry; exit when
close crosses back above its own `exit_sma_window`-day SMA (source's "returns
to the mean" exit) or a `max_hold_days` time-stop (this repo's standard
safety exit since the source gives no explicit day count).

GAPO formula (Chande's definition, as stated across multiple sources
including stockcharts.com/chartschool and lightningchart.com):
    GAPO = ln( sum(High-Low, n) / Range(High,Low,n) ) / ln(n)
where Range(High,Low,n) is the max High minus min Low over the trailing n
bars, and sum(High-Low, n) is the sum of each individual bar's daily range
over the same window. Values near 0 = trending/smooth (bar ranges nest
tightly inside the n-bar envelope); values near 1 = choppy/complex (each
bar's range approaches the full n-bar envelope on its own).

First GAPO-family strategy in this repo -- distinct from every existing
volatility-regime-gated mean reversion strategy (BB-width squeeze, ATR
percentile, Choppiness Index, TTM Squeeze) since GAPO is a genuinely
different (log-fractal-dimension) volatility construction, and distinct
from every RSI-family strategy already tested (RSI(2), Connors RSI, RMI,
QS RSI) via this specific GAPO-gated low-vol regime filter replacing their
trend/SMA/volume filters.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
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


def _gapo(high: pd.Series, low: pd.Series, window: int) -> pd.Series:
    """Gopalakrishnan Range Index: ln(sum(H-L,n) / (max(H,n)-min(L,n))) / ln(n)."""
    daily_range = (high - low).clip(lower=1e-12)
    sum_range = daily_range.rolling(window).sum()
    envelope = high.rolling(window).max() - low.rolling(window).min()
    envelope = envelope.clip(lower=1e-12)
    gapo = np.log(sum_range / envelope) / np.log(window)
    return gapo


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    gapo_window: int = 20,
    gapo_threshold: float = 0.3,
    rsi_window: int = 3,
    rsi_oversold: float = 20.0,
    exit_sma_window: int = 10,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    gapo = _gapo(high, low, gapo_window)
    rsi = _rsi(close, rsi_window)
    exit_sma = close.rolling(exit_sma_window).mean()

    low_vol_regime = gapo < gapo_threshold
    oversold = rsi <= rsi_oversold
    entry_signal = (low_vol_regime & oversold).fillna(False)
    exit_signal = (close > exit_sma).fillna(False)

    entry_arr = entry_signal.to_numpy()
    exit_arr = exit_signal.to_numpy()
    n = len(df)
    pos_arr = np.zeros(n, dtype=int)

    in_pos = False
    hold_counter = 0
    for i in range(n):
        if in_pos:
            hold_counter += 1
            if exit_arr[i] or hold_counter >= max_hold_days:
                in_pos = False
                hold_counter = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold_counter = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    gapo_window: int = 20,
    gapo_threshold: float = 0.3,
    rsi_window: int = 3,
    rsi_oversold: float = 20.0,
    exit_sma_window: int = 10,
    max_hold_days: int = 10,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        gapo_window=gapo_window,
        gapo_threshold=gapo_threshold,
        rsi_window=rsi_window,
        rsi_oversold=rsi_oversold,
        exit_sma_window=exit_sma_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
