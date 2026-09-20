"""Strategy: TASC July 2026 "Risk-On, Risk-Off, Or Caution" regime-based
exposure dial (Gaetano Di Prima & Fabio Baruffa).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-163):
Per TradingView's PineCodersTASC implementation of Di Prima & Baruffa's July
2026 TASC Traders' Tips article "Market Regime Identification Using Trend,
Volatility, And Credit Conditions" (read via browser_exec after web_search's
DDGS/Yahoo backend TLS-erroring), a weekly regime classifier combines THREE
independent conditions to size exposure to a benchmark (SPX/SPY in the
source, adapted here to whichever symbol is passed in -- e.g. QQQ):
  1. Trend: SPX above its 200-day SMA.
  2. Volatility term-structure: VIX < VIX3M (short-term vol calm relative to
     3-month vol -- backwardation/inversion signals stress).
  3. Credit risk appetite: 100-day MA of the rolling Z-score of the
     HYG/IEF ratio (junk-bond-vs-treasury) is positive.
If all 3 favorable -> full exposure (1.0). If 2/3 favorable -> half exposure
(0.5). If <=1/3 favorable -> flat (0.0). Rebalanced weekly. This is a new
technique for this repo: prior regime-gate strategies here use a SINGLE
filter dimension (vol-only, trend-only, etc.); this is the first THREE-WAY
graduated-exposure regime dial combining trend + vol-term-structure +
credit-spread-appetite as independent votes (0 prior KB hits for
"Risk-On Risk-Off Caution").

Signal logic
------------
- Uses the TRADED symbol's own price for the trend filter (close vs its
  own SMA(200)) rather than literally SPX, so the strategy is self-
  contained per generate_returns_fn's single-price_df contract; VIX/VIX3M
  and HYG/IEF are fetched as fixed auxiliary tickers via data/loaders.py
  inside generate_signals (acceptable since these are genuinely different
  instruments providing macro context, not another view of the same
  traded asset).
- Trend condition: close > close.rolling(200).mean().
- Vol condition: VIX_close < VIX3M_close (aligned to the price_df's index).
- Credit condition: rolling 100-day MA of the (window-day) Z-score of
  HYG_close/IEF_close > 0.
- Weekly rebalance: on each bar that is the first trading day of the ISO
  week (Monday, using price_df's own trading calendar), evaluate all 3
  conditions and set position weight per the 3/2/<=1 rule; hold that
  weight until the next weekly rebalance point.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (position WEIGHT
        series in [0, 0.5, 1.0] -- NOT strictly {0,1}, same continuous-
        sizing convention already used elsewhere in this repo, e.g.
        strategies/2026-09-20_leveraged_defensive_compounder.py)
"""

from __future__ import annotations

import sys
import os
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_aux(symbol: str, start, end) -> pd.Series:
    from loaders import load_equity

    df = load_equity(symbol, start, end, interval="1d")
    df = _prep(df)
    return df["close"]


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    credit_zscore_window: int = 100,
    credit_ma_window: int = 100,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure-weight series."""
    df = _prep(price_df)
    close = df["close"]

    start = close.index.min() - pd.Timedelta(days=400)
    end = close.index.max() + pd.Timedelta(days=5)

    vix = _load_aux("^VIX", start, end).reindex(close.index).ffill()
    vix3m = _load_aux("^VIX3M", start, end).reindex(close.index).ffill()
    hyg = _load_aux("HYG", start, end).reindex(close.index).ffill()
    ief = _load_aux("IEF", start, end).reindex(close.index).ffill()

    trend_ok = close > close.rolling(trend_window).mean()

    vol_ok = vix < vix3m

    hyg_ief_ratio = hyg / ief
    ratio_mean = hyg_ief_ratio.rolling(credit_zscore_window).mean()
    ratio_std = hyg_ief_ratio.rolling(credit_zscore_window).std()
    zscore = (hyg_ief_ratio - ratio_mean) / ratio_std
    credit_ma = zscore.rolling(credit_ma_window).mean()
    credit_ok = credit_ma > 0

    votes = trend_ok.astype(int) + vol_ok.astype(int) + credit_ok.astype(int)

    is_monday = close.index.to_series().dt.dayofweek == 0
    # Fallback: if a given week has no Monday bar (holiday), use the first
    # bar of that ISO week instead.
    iso_week = close.index.to_series().dt.isocalendar().week
    iso_year = close.index.to_series().dt.isocalendar().year
    week_key = list(zip(iso_year, iso_week))
    first_of_week = pd.Series(week_key, index=close.index).ne(
        pd.Series(week_key, index=close.index).shift(1)
    )
    rebalance_point = (is_monday | first_of_week).fillna(True)

    weight = pd.Series(0.0, index=close.index)
    current_weight = 0.0
    for i in range(len(close)):
        if bool(rebalance_point.iloc[i]) and not pd.isna(votes.iloc[i]):
            v = votes.iloc[i]
            if v == 3:
                current_weight = 1.0 * leverage_cap
            elif v == 2:
                current_weight = 0.5 * leverage_cap
            else:
                current_weight = 0.0
        weight.iloc[i] = current_weight

    return weight


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Weight-scaled daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    weight = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = weight.shift(1).fillna(0) * daily_ret
    return strategy_ret
