"""Strategy: Pring's Know Sure Thing (KST) signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per stockcharts.com ChartSchool's "Pring's Know Sure Thing (KST)" page
(visited this iteration via browser_exec, web_search DDGS backend TLS
connection-errored on the query): KST is a momentum oscillator that
combines FOUR separately-smoothed rate-of-change (ROC) measurements at
different lookback periods into a single weighted-sum line (shortest ROC
weighted x1, longest weighted x4), plus a signal line (simple moving
average of KST itself). Martin Pring's own stated preference ("the basic
centerline and signal line crossovers are usually the most robust ... KST's
creator favors signal line crossovers ... for signals") is: go long when
KST crosses above its signal line, flat/short when KST crosses below its
signal line. Default short-term/daily parameterization per the source:
KST(10,15,20,30, 10,10,10,15, 9) -- i.e. ROC periods {10,15,20,30} each
smoothed with an SMA of length {10,10,10,15} respectively, weighted
{1,2,3,4}, and a 9-period signal-line SMA.

This is a genuinely distinct construction from every other momentum
oscillator strategy already in this repo (MACD, RSI, Coppock Curve,
Ultimate Oscillator, DPO, etc.) -- KST is the only one that sums FOUR
independently-smoothed ROC measurements across different timeframes with
increasing weights, explicitly designed to blend several distinct price
cycles into one signal (Pring describes it as "closely resembles TRIX" but
built from 4 ROC/MA legs rather than one triple-smoothed EMA). 0 prior KST
entries in this repo.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _kst(
    close: pd.Series,
    roc1: int, roc2: int, roc3: int, roc4: int,
    sma1: int, sma2: int, sma3: int, sma4: int,
    signal_period: int,
):
    """Compute the KST line and its signal line.

    KST = 1*SMA(ROC(roc1), sma1) + 2*SMA(ROC(roc2), sma2)
        + 3*SMA(ROC(roc3), sma3) + 4*SMA(ROC(roc4), sma4)
    signal = SMA(KST, signal_period)
    """
    def roc_pct(n: int) -> pd.Series:
        return close.pct_change(n) * 100.0

    leg1 = roc_pct(roc1).rolling(sma1).mean()
    leg2 = roc_pct(roc2).rolling(sma2).mean()
    leg3 = roc_pct(roc3).rolling(sma3).mean()
    leg4 = roc_pct(roc4).rolling(sma4).mean()

    kst = 1 * leg1 + 2 * leg2 + 3 * leg3 + 4 * leg4
    signal = kst.rolling(signal_period).mean()
    return kst, signal


def generate_signals(
    price_df: pd.DataFrame,
    roc1: int = 10,
    roc2: int = 15,
    roc3: int = 20,
    roc4: int = 30,
    sma1: int = 10,
    sma2: int = 10,
    sma3: int = 10,
    sma4: int = 15,
    signal_period: int = 9,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: KST crosses above its signal line.
    Exit to flat: KST crosses below its signal line.
    Per Pring's own stated preference for KST's most robust signal.
    """
    df = _prep(price_df)
    close = df["close"]

    kst, signal = _kst(close, roc1, roc2, roc3, roc4, sma1, sma2, sma3, sma4, signal_period)

    above = kst > signal
    position = above.fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
