"""Strategy: Slope Divergence (stochastic-momentum-slope vs price-slope
majority-vote divergence), per "Slope Divergence: Capitalizing On
Uncertainty" (Perry J. Kaufman, TASC June 2014). Read this iteration via
browser_exec at https://traders.com/documentation/feedbk_docs/2014/06/traderstips.html
(MetaStock formulas disclosed directly in the article's Traders' Tips code
section, credited to William Golson/MetaStock Technical Support).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-120):
Compute a raw stochastic %K of price over `stoch_period` (25 in source).
Take the linear-regression SLOPE of that stochastic over 3 different short
lookbacks (5, 12, 14 bars) -- md1/md2/md3 -- and the linear-regression SLOPE
of price (close) over the SAME 3 lookbacks -- pd1/pd2/pd3. Kaufman's
"divergence" signal (deliberately reversing the conventional
bearish-divergence reading, per the article's own title "capitalizing on
uncertainty") fires a LONG entry when a MAJORITY (>=2 of 3) of the momentum
slopes are NEGATIVE while a MAJORITY of the price slopes are POSITIVE --
i.e. price is still rising but the underlying stochastic-momentum is
turning down across multiple lookback windows -- Kaufman's own contrarian
thesis being that this "uncertain" majority-vote divergence, rather than a
strict single-indicator crossover, is itself tradeable. Exit when either ALL
6 slopes turn positive (min>0) or ALL 6 turn negative (max<0) -- i.e. full
directional agreement across momentum AND price, per the source's disclosed
"Sell Order" rule (applies symmetrically to both long-exit and short-cover
in the source; used here as the single long-exit rule). This is distinct
from the repo's existing divergence-family entries (e.g. rsi_bullish_divergence,
macd_histogram_bullish_divergence, obv_bullish_divergence_reversal) because
none use a MAJORITY-VOTE across 3 lookback windows applied to BOTH momentum
slope AND price slope simultaneously -- this is a genuinely different,
noise-robust multi-window divergence construction.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
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


def _stochastic_k(close: pd.Series, high: pd.Series, low: pd.Series, period: int) -> pd.Series:
    hh = high.rolling(period).max()
    ll = low.rolling(period).min()
    rng = hh - ll
    k = 100.0 * (close - ll) / rng.replace(0, np.nan)
    return k.fillna(50.0)


def _rolling_linreg_slope(series: pd.Series, window: int) -> pd.Series:
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    def _slope(vals: np.ndarray) -> float:
        y = vals
        return float(((x - x_mean) * (y - y.mean())).sum() / x_var)

    return series.rolling(window).apply(_slope, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    stoch_period: int = 25,
    slope_period_1: int = 5,
    slope_period_2: int = 12,
    slope_period_3: int = 14,
) -> pd.Series:
    """Return a {0,1} long/flat position series per Kaufman's Slope
    Divergence majority-vote rule (long-only adaptation)."""
    df = _prep(price_df)
    close, high, low = df["close"], df["high"], df["low"]

    mi = _stochastic_k(close, high, low, stoch_period)

    md1 = _rolling_linreg_slope(mi, slope_period_1)
    md2 = _rolling_linreg_slope(mi, slope_period_2)
    md3 = _rolling_linreg_slope(mi, slope_period_3)
    pd1 = _rolling_linreg_slope(close, slope_period_1)
    pd2 = _rolling_linreg_slope(close, slope_period_2)
    pd3 = _rolling_linreg_slope(close, slope_period_3)

    md_neg_votes = (md1 < 0).astype(int) + (md2 < 0).astype(int) + (md3 < 0).astype(int)
    pd_pos_votes = (pd1 > 0).astype(int) + (pd2 > 0).astype(int) + (pd3 > 0).astype(int)

    entry = (md_neg_votes >= 2) & (pd_pos_votes >= 2)

    all_slopes = pd.concat([md1, md2, md3, pd1, pd2, pd3], axis=1)
    exit_full_agreement = (all_slopes.min(axis=1) > 0) | (all_slopes.max(axis=1) < 0)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        if in_position:
            if bool(exit_full_agreement.iloc[i]):
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
