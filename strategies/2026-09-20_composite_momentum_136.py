"""Strategy: Composite Momentum 1-3-6 with 200-day trend safety filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per https://help.investminder.com/en/investment-academy/practical-guide-
composite-momentum-1-3-6-3-6-12-1vqehob/ ("Practical Guide: Composite
Momentum (1-3-6 & 3-6-12)"): rather than a single rate-of-change lookback,
average several simultaneous ROC horizons to capture a "robust and
sustainable" trend and filter out ephemeral single-timeframe moves. The
"tactical" 1-3-6 variant averages 1-month, 3-month, and 6-month ROC.
The source's own explicitly-disclosed "Safety Filter" rule: "Buy if
Composite Momentum > 0 AND Current Price > 200-day Moving Average" --
this is the exact rule this strategy implements (source frames Composite
Momentum primarily as a cross-sectional RANKING tool for sector rotation,
but also gives this single-asset absolute-threshold timing rule as its
"safety filter" variant, which is what we test here).

Signal logic:
    composite_mom = mean(ROC(close, 21), ROC(close, 63), ROC(close, 126))
        (21/63/126 trading days approximating 1/3/6 calendar months)
    Long when composite_mom > mom_threshold (default 0.0) AND
        close > SMA(trend_window) (default 200).
    Flat otherwise.

First "Composite Momentum 1-3-6" multi-horizon-averaged-ROC strategy in
this repo -- distinct from the already-tested Coppock Curve (WMA-smoothed
DIFFERENCE of two ROCs, not a simple average of three) and the
multi-horizon time-series-momentum VOTE strategy (2026-09-08-132, which
counts how many of several horizons are individually positive rather than
averaging their magnitudes into one continuous score).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1})
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if len(df.index) > 1:
        median_gap = pd.Series(df.index).diff().median()
        if pd.notna(median_gap) and median_gap < pd.Timedelta(hours=20):
            df = df.resample("1D").agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            ).dropna()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    roc1: int = 21,
    roc2: int = 63,
    roc3: int = 126,
    trend_window: int = 200,
    mom_threshold: float = 0.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    roc_1 = close.pct_change(roc1)
    roc_2 = close.pct_change(roc2)
    roc_3 = close.pct_change(roc3)
    composite_mom = (roc_1 + roc_2 + roc_3) / 3.0

    trend_ok = close > close.rolling(trend_window).mean()
    mom_ok = composite_mom > mom_threshold

    position = (trend_ok.fillna(False) & mom_ok.fillna(False)).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
