"""Strategy: Excess-Return Multi-Moving-Average (ER_MMA) Ensemble Tiered Exposure.

Hypothesis (2026-09-23, 6th iteration this cron trigger):
Per https://algorithmicfire.com/post/defending-your-savings-against-significant-downturns
("Defending Your Savings Against Significant Downturns", AlgorithmicFIRE,
found via browser_exec after web_search DDGS/Yahoo backend TLS-errored this
iteration): the "Excess Return" family of trend-following strategies
computes each day's EXCESS return (asset return minus the risk-free rate,
proxied here by ^IRX, the 13-week T-bill yield, converted to a daily rate)
rather than raw asset price, then applies a moving-average trend rule to
that excess-return series. The source's own headline finding: across 108
stock ETFs, the ensemble "Excess Return MMA" (Multi-Moving-Average) variant
that blends MULTIPLE lookback windows into a TIERED exposure (0%, 33.3%,
66.7%, 100% invested based on how many of the moving-average signals agree)
cut median max drawdown from -51.3% (buy & hold) to -21.4%, while only
giving up 0.9pp of median CAGR (9.8% vs 10.7%) and raising median Sharpe
from 0.51 to 0.72 -- outperforming both the single-line "Excess Return SMA"
binary variant (-28.9% MDD) and the classic golden-cross Moving Average
strategy (-24.8% MDD) on drawdown reduction specifically.

Operationalized here: compute a rolling cumulative excess-return moving
average at N=3 distinct lookback windows (short/mid/long). Each window
votes "risk-on" if its own excess-return moving average is > 0. Exposure
tiers to {0, 1/3, 2/3, 1.0} based on how many of the 3 windows vote
risk-on (0/3, 1/3, 2/3, 3/3 respectively) -- this IS the source's own
disclosed multi-MA-ensemble tiering mechanism (0%, 33.3%, 66.7%, 100%).

Distinct from every existing strategy in this repo: this repo has several
multi-horizon momentum VOTE constructions (2026-09-08-132 votes on raw
trailing-return SIGN across horizons; 2026-09-20-090/2026-09-22-040 use
composite/weighted RAW return magnitudes), but NONE compare EXCESS return
(net of a risk-free-rate benchmark) via a moving-average trend rule with
TIERED {0,1/3,2/3,1} exposure scaling by window-agreement count -- the
risk-free-rate netting and the specific 4-tier exposure ladder are both
new to this repo.
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _naive_index(idx):
    return idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx


def _get_riskfree_daily_return(idx: pd.DatetimeIndex) -> pd.Series:
    from loaders import load_equity

    lookback_days = 400
    start = (idx.min() - pd.Timedelta(days=lookback_days)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()
    irx = load_equity("^IRX", start, end).set_index("timestamp")["close"].sort_index()
    irx.index = _naive_index(irx.index)
    # ^IRX quotes an annualized discount-rate-style yield in percent (e.g. 4.5 = 4.5%/yr).
    # Convert to an approximate daily return: (yield/100) / 252.
    daily_rf = (irx / 100.0) / 252.0

    target_idx = _naive_index(idx)
    daily_rf = daily_rf.reindex(daily_rf.index.union(target_idx)).sort_index().ffill()
    daily_rf = daily_rf.reindex(target_idx)
    daily_rf.index = idx
    return daily_rf.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    short_window: int = 20,
    mid_window: int = 60,
    long_window: int = 150,
    rebalance_days: int = 5,
    is_crypto: bool = False,
) -> pd.Series:
    """Return a continuous {0, 1/3, 2/3, 1} exposure series based on how many
    of 3 excess-return moving-average windows vote risk-on (excess-return MA > 0).

    `rebalance_days` (default 5, i.e. weekly) throttles how often the tiered
    exposure signal is allowed to change -- the source's own "smoother
    transitions" claim assumes infrequent reallocation (its own backtest
    reports turnover in trades/year, not trades/day); recomputing the vote
    daily on noisy short-window excess-return MAs otherwise produces far
    more turnover than the source's own reported trade counts.
    """
    df = _prep(price_df)
    idx = df.index
    close = df["close"]
    asset_daily_ret = close.pct_change().fillna(0.0)

    if is_crypto:
        # No US T-bill risk-free analog for 24/7 crypto -- use raw return (rf=0)
        # as the excess-return proxy (falsification-style test).
        rf_daily = pd.Series(0.0, index=idx)
    else:
        try:
            rf_daily = _get_riskfree_daily_return(idx)
        except Exception:
            rf_daily = pd.Series(0.0, index=idx)

    excess_ret = asset_daily_ret - rf_daily

    windows = [short_window, mid_window, long_window]
    votes = pd.DataFrame(index=idx)
    for w in windows:
        ma = excess_ret.rolling(w, min_periods=max(2, w // 2)).mean()
        votes[str(w)] = (ma > 0).astype(int)

    vote_count = votes.sum(axis=1)
    raw_exposure = (vote_count / len(windows)).fillna(0.0)

    # Sample the raw exposure only every `rebalance_days` bars, holding the
    # last sampled value in between (throttled rebalancing).
    n = len(raw_exposure)
    sample_mask = pd.Series(False, index=raw_exposure.index)
    sample_mask.iloc[::max(1, rebalance_days)] = True
    exposure = raw_exposure.where(sample_mask).ffill().fillna(0.0)
    exposure.index = idx
    return exposure


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs). Exposure lagged by 1 day."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
