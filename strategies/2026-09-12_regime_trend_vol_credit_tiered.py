"""Strategy: 3-Factor Regime Allocation (Trend, Volatility, Credit) -- TASC 2026.07.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per TASC July 2026 Traders' Tips, "Market Regime Identification Using Trend,
Volatility, And Credit Conditions" (Gaetano Di Prima & Fabio Baruffa), via
https://www.tradingview.com/script/wu1VhNpf-TASC-2026-07-Risk-On-Risk-Off-Or-Caution/
(exact rules fully disclosed on the script's own overview page):

Three weekly boolean conditions define market regime:
  1. Trend Filter: underlying close > its own 200-day SMA.
  2. Volatility Filter: VIX < VIX3M (short-term vol below 3-month vol --
     i.e. NOT in stress-driven backwardation).
  3. Risk Appetite: 100-day rolling Z-score of the HYG/IEF price ratio is
     positive (credit markets showing risk-on appetite).

At the end of every week, count how many of the 3 conditions are favorable
and set next week's exposure accordingly (order executed at next Monday's
open, per the source's own rule):
  - 3/3 favorable -> full exposure (position=1.0)
  - 2/3 favorable -> half exposure (position=0.5)
  - 0-1/3 favorable -> no exposure (position=0.0)

This is the first fractional-position-weight, 3-factor regime-tiered
strategy in this repo tested on the SPY/QQQ underlying itself (distinct
from the already-tested single-factor versions of each ingredient: VIX/
VIX3M term structure alone -- 2026-09-04-157/2026-09-05-028, both
near-miss/rejected; HYG/LQD credit spread alone -- 2026-09-05-025,
rejected; 200-day SMA trend filter alone -- ubiquitous baseline in this
repo). The combination + tiered 0/50/100% exposure scheme (rather than a
binary in/out) is the novel element being tested.

Data note: VIX3M is fetched via yfinance ticker "^VIX3M" and IEF/HYG are
standard ETF tickers, all retrievable through data/loaders.py::load_equity
(no new data-fetching logic needed).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series

NOTE: because this strategy needs auxiliary series (VIX, VIX3M, HYG, IEF)
beyond the single `price_df` the grid-test/validator harness passes in,
`generate_signals`/`generate_returns` fetch those auxiliary series
internally via `data.loaders.load_equity` keyed off the same start/end date
range as `price_df`, rather than expecting them as extra positional args
(keeps the required generate_signals(price_df, **params) contract intact).
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fetch_aux(index: pd.DatetimeIndex):
    from loaders import load_equity

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()

    vix = load_equity("^VIX", start=start, end=end)
    vix3m = load_equity("^VIX3M", start=start, end=end)
    hyg = load_equity("HYG", start=start, end=end)
    ief = load_equity("IEF", start=start, end=end)

    def _close(df):
        d = df.copy()
        if "timestamp" in d.columns:
            d = d.set_index("timestamp")
        return d.sort_index()["close"]

    return _close(vix), _close(vix3m), _close(hyg), _close(ief)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    credit_zscore_window: int = 100,
    full_exposure_favorable: int = 3,
    half_exposure_favorable: int = 2,
) -> pd.Series:
    """Return a fractional {0.0, 0.5, 1.0} position series (weekly-updated,
    forward-filled to daily)."""
    df = _prep(price_df)
    close = df["close"]

    vix, vix3m, hyg, ief = _fetch_aux(close.index)

    # Trend condition
    sma_trend = close.rolling(trend_window).mean()
    cond_trend = close > sma_trend

    # Volatility condition: VIX < VIX3M, aligned to close's index
    vix_aligned = vix.reindex(close.index).ffill()
    vix3m_aligned = vix3m.reindex(close.index).ffill()
    cond_vol = vix_aligned < vix3m_aligned

    # Credit condition: rolling z-score of HYG/IEF ratio > 0
    hyg_aligned = hyg.reindex(close.index).ffill()
    ief_aligned = ief.reindex(close.index).ffill()
    ratio = hyg_aligned / ief_aligned
    ratio_mean = ratio.rolling(credit_zscore_window).mean()
    ratio_std = ratio.rolling(credit_zscore_window).std()
    z = (ratio - ratio_mean) / ratio_std
    cond_credit = z > 0

    favorable_count = (
        cond_trend.astype(int).fillna(0)
        + cond_vol.astype(int).fillna(0)
        + cond_credit.astype(int).fillna(0)
    )

    # Weekly assessment: use each week's Friday-close favorable_count value,
    # apply it starting the following Monday (source's own execution rule).
    weekly_count = favorable_count.resample("W-FRI").last()
    daily_target = weekly_count.reindex(close.index, method="ffill")

    position = pd.Series(0.0, index=close.index)
    position[daily_target >= full_exposure_favorable] = 1.0
    position[daily_target == half_exposure_favorable] = 0.5
    position[daily_target < half_exposure_favorable] = 0.0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
