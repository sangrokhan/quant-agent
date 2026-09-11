"""Strategy: "Defense First" tactical-asset-allocation gate (Thomas Carlson /
Allocate Smartly construction), single-asset-interface adaptation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-081):
Per Thomas Carlson's "Defense First" strategy as summarized by
QuantifiedStrategies.com
(https://www.quantifiedstrategies.com/alternative-60-40-portfolio/, visited
this iteration), a tactical model tracks four DEFENSIVE assets -- long
Treasuries (TLT), gold (GLD), commodities (DBC, PDBC-equivalent), and the US
dollar (UUP) -- each asset's momentum being the AVERAGE of its 1, 3, 6, and
12-month returns. Whenever a defensive asset's own momentum falls below the
T-bill risk-free rate (proxied here by BIL's own trailing return over the
matching window), that asset's would-be allocation shifts to US stocks
(SPY) instead. The source's own key finding: individually each defensive
asset is a weak/mixed predictor, but when MULTIPLE defensive assets
simultaneously show weak momentum (below the risk-free rate), the
predictive power for elevated forward stock returns strengthens
materially (2 assets agreeing -> moderate; 3+ agreeing -> strong).

This is distinct from the previously-tested and REJECTED
2026-09-08-147 gold-momentum risk-off gate (which used a single asset,
GLD's own absolute momentum vs. a fixed threshold, as a binary flat/full
circuit-breaker) in three structural ways: (1) uses all 4 Defense-First
assets (TLT/GLD/DBC/UUP), not just GLD; (2) uses the source's own
multi-period-averaged (1/3/6/12mo) momentum definition, not a single
trailing-window return; (3) implements a GRADED continuous equity weight
(count of underperforming defensive assets / 4) rather than a binary
gate -- directly testing the source's own "collective signal strength"
finding (weight scales with how many defensive assets agree) rather than
a single-asset on/off switch.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (weight in [0,1])

Primary asset (price_df) is intended to be SPY or QQQ (equity) or a crypto
pair (BTC/USDT, ETH/USDT) for the grid's cross-asset-class arm -- for
crypto, the defensive-asset basket is still the traditional TLT/GLD/DBC/UUP
(there is no crypto-native "defensive" analog in this repo's loaders), which
is itself a testable claim: does a TradFi defensive-weakness signal have any
predictive power for BTC/ETH forward returns?
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    """Set timestamp as index but PRESERVE its original tz-awareness --
    grid_test.py's own vol-regime masks are built from the same tz-aware
    price_df, so stripping tz here would desync the reindex and silently
    zero out every regime slice."""
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _avg_momentum(close: pd.Series, months: tuple = (1, 3, 6, 12)) -> pd.Series:
    """Average of trailing N-month simple returns on a daily series
    (approximated as N*21 trading days), per the source's own definition."""
    total = None
    for m in months:
        window = m * 21
        ret = close.pct_change(window)
        total = ret if total is None else total.add(ret, fill_value=None)
    return (total / len(months))


def _defensive_basket_underperf_count(
    index: pd.DatetimeIndex,
    rf_threshold_bps_per_day: float,
) -> pd.Series:
    """For each day in index, count how many of {TLT, GLD, DBC, UUP} have
    average (1/3/6/12mo) momentum BELOW the T-bill (BIL) proxy momentum
    (same averaging window, same day) -- i.e. how many "shift to stocks"."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = (index.min() - pd.Timedelta(days=450)).to_pydatetime()
    end = (index.max() + pd.Timedelta(days=10)).to_pydatetime()

    defensive_syms = ["TLT", "GLD", "DBC", "UUP"]
    rf_sym = "BIL"

    def _get_mom(sym: str) -> pd.Series:
        df = load_equity(sym, start, end)
        close = df.set_index("timestamp")["close"] if "timestamp" in df.columns else df["close"]
        close.index = pd.to_datetime(close.index)
        if close.index.tz is not None:
            close.index = close.index.tz_localize(None)
        close = close[~close.index.duplicated(keep="last")].sort_index()
        return _avg_momentum(close)

    rf_mom = _get_mom(rf_sym)
    # BIL's own avg momentum is a tiny positive number; add a small fixed
    # floor (rf_threshold_bps_per_day, annualized-ish bps) as the source's
    # T-bill "hurdle rate" buffer to avoid noise-driven flips right at zero.
    rf_hurdle = rf_mom + (rf_threshold_bps_per_day / 10000.0)

    underperf_count = pd.Series(0.0, index=rf_hurdle.index)
    for sym in defensive_syms:
        mom = _get_mom(sym)
        aligned_mom, aligned_rf = mom.align(rf_hurdle, join="inner")
        underperf = (aligned_mom < aligned_rf).astype(float)
        underperf_count = underperf_count.add(underperf, fill_value=0.0)

    # `underperf_count`'s index is naive (tz stripped in _get_mom); `index`
    # (the caller's price_df index) may be tz-aware -- normalize both to
    # naive calendar dates for the reindex/ffill, then re-attach the
    # ORIGINAL (possibly tz-aware) index labels so downstream alignment
    # against price_df/grid_test's vol-regime masks stays consistent.
    naive_index = pd.DatetimeIndex(index).tz_localize(None) if pd.DatetimeIndex(index).tz is not None else pd.DatetimeIndex(index)
    daily = underperf_count.reindex(naive_index, method="ffill").fillna(0.0)
    daily.index = index
    return daily


def generate_signals(
    price_df: pd.DataFrame,
    rf_threshold_bps_per_day: float = 5.0,
    rebalance_freq: str = "W",
) -> pd.Series:
    """Return a [0,1] continuous weight series for the primary asset:
    weight = (# of 4 defensive assets underperforming the T-bill hurdle) / 4.
    Rebalanced weekly (source uses monthly; weekly is a modest refinement
    to reduce staleness while keeping turnover low) via forward-fill."""
    df = _prep(price_df)
    close = df["close"]

    underperf_count = _defensive_basket_underperf_count(close.index, rf_threshold_bps_per_day)
    weight_raw = (underperf_count / 4.0).clip(0.0, 1.0)

    # Rebalance only on a periodic schedule (weekly), forward-filled between,
    # to keep turnover low per the source's own monthly-rebalance spirit.
    resampled = weight_raw.resample(rebalance_freq).last()
    resampled_shifted = resampled.shift(1)  # decision at period end applies to next period
    weight = resampled_shifted.reindex(close.index, method="ffill").fillna(0.0)
    return weight


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Weight-scaled daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    weight = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = weight.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
