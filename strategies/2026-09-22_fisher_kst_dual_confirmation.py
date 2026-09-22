"""Strategy: Fisher Transform + KST Histogram dual-confirmation momentum.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-073):
Per a Medium article series by kridtapon on MOS stock ("Outsmarting Buy &
Hold with Logic: MOS Stock Strategy" / "Adaptive Strategy Testing with
Fisher Transform & KST Indicators" / "Adaptive Momentum Strategy for MOS
Stock: Fisher Transform & KST", found via Google SERP -- web_search's DDGS
backend returning empty/garbage results for several queries this iteration,
individual Medium article URLs 404 when navigated to directly but the
Google SERP snippets themselves disclose the exact rule): entry (buy)
signal occurs when BOTH the Ehlers Fisher Transform is above zero AND the
KST (Know Sure Thing, Martin Pring) histogram (KST line minus its 9-period
signal line) is also above zero -- a dual-confirmation of upward momentum
across two structurally different oscillator families (a price-normalizing
transform vs a multi-timeframe smoothed rate-of-change composite). Exit
when both indicators turn negative again (source's disclosed exit
condition per the SERP snippet: "An exit (sell) signal occurs when...").
Repo has 26 prior Fisher Transform entries (extreme-threshold-crossover,
trend-filtered, RSI/CCI/Stochastic/RVI Fisher-of-oscillator variants,
continuous-sizing dials) and 10+ prior Coppock Curve entries (a different
Pring composite-ROC oscillator), but zero prior KST (Know Sure Thing, the
sum of 4 differently-weighted smoothed ROC periods) entries and zero prior
Fisher+KST combination -- first test of this specific dual-confirmation
pairing in this repo.

KST formula (standard, Martin Pring):
    KST = 1*SMA(ROC(close,10),10) + 2*SMA(ROC(close,15),10)
        + 3*SMA(ROC(close,20),10) + 4*SMA(ROC(close,30),15)
    signal = SMA(KST, 9)
    histogram = KST - signal

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fisher_transform(close: pd.Series, window: int = 10) -> pd.Series:
    low_n = close.rolling(window).min()
    high_n = close.rolling(window).max()
    rng = (high_n - low_n).replace(0, pd.NA)
    raw = 2 * ((close - low_n) / rng - 0.5)
    raw = raw.fillna(0.0)

    smoothed = pd.Series(index=close.index, dtype=float)
    prev_smoothed = 0.0
    prev_fisher = 0.0
    fisher = pd.Series(index=close.index, dtype=float)
    for idx in close.index:
        v = raw.loc[idx]
        s = 0.33 * v + 0.67 * prev_smoothed
        s = max(min(s, 0.999), -0.999)
        smoothed.loc[idx] = s
        f = 0.5 * math.log((1 + s) / (1 - s)) + 0.5 * prev_fisher
        fisher.loc[idx] = f
        prev_smoothed = s
        prev_fisher = f
    return fisher


def _kst_histogram(
    close: pd.Series,
    roc1: int = 10, sma1: int = 10,
    roc2: int = 15, sma2: int = 10,
    roc3: int = 20, sma3: int = 10,
    roc4: int = 30, sma4: int = 15,
    signal_window: int = 9,
) -> pd.Series:
    def roc(series: pd.Series, n: int) -> pd.Series:
        return (series / series.shift(n) - 1.0) * 100.0

    k1 = roc(close, roc1).rolling(sma1).mean()
    k2 = roc(close, roc2).rolling(sma2).mean()
    k3 = roc(close, roc3).rolling(sma3).mean()
    k4 = roc(close, roc4).rolling(sma4).mean()
    kst = 1 * k1 + 2 * k2 + 3 * k3 + 4 * k4
    signal = kst.rolling(signal_window).mean()
    return kst - signal


def generate_signals(
    price_df: pd.DataFrame,
    fisher_window: int = 10,
    trend_window: int = 0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fisher = _fisher_transform(close, window=fisher_window)
    kst_hist = _kst_histogram(close)

    if trend_window and trend_window > 0:
        sma = close.rolling(trend_window).mean()
        uptrend = close > sma
    else:
        uptrend = pd.Series(True, index=df.index)

    entry = (fisher > 0) & (kst_hist > 0) & uptrend
    exit_signal = (fisher < 0) & (kst_hist < 0)

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
