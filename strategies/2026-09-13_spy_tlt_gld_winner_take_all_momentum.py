"""Strategy: 3-asset (SPY/TLT/GLD) winner-take-all 6-month momentum rotation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-13-XXX):
Per https://edgelabtrading.com/blog/etf-momentum-rotation (read via
browser_exec this iteration), the classic "one decision a month: hold
whichever of stocks, bonds, or gold has the strongest six-month momentum"
ETF rotation strategy: on the last trading day of each month, rank SPY
(US stocks), TLT (20+ year Treasuries), and GLD (gold) by trailing 6-month
total return; hold the single winner 100% for the following month;
repeat. Source's own 21-year backtest (2005-2026): out-of-sample
(2016-2026) CAGR 10.9%/Sharpe 0.70/MDD -33.6%; full-period CAGR 9.4%/
Sharpe 0.61/MDD -25.8% (vs an equal-weight-all-three benchmark's Sharpe
0.96 -- source's own finding is that this WINNER-TAKE-ALL concentration is
NOT clearly better than simply holding all three untouched).

This is structurally distinct from the already-tested/accepted Faber
3-asset EQUAL-WEIGHT-ALL-QUALIFYING rotation (2026-09-11-078, holds
1/N of whichever assets pass an ABSOLUTE 3mo>10mo SMA trend filter) and
the already-tested/rejected 5-asset GTAA dual-momentum
(2026-09-11-037/-041): this strategy (a) uses only 3 assets
(SPY/TLT/GLD, not 5), (b) concentrates 100% in the single top-ranked
asset by trailing 6-month return (pure cross-sectional RELATIVE
momentum, no absolute-momentum/trend-filter component at all -- always
invested in whichever asset ranks highest, even if all three have
negative momentum), and (c) uses a fixed single 6-month lookback (the
source's own comparison found 12-month "worse on every metric").
Adapted to this repo's single-asset generate_signals/generate_returns
interface: the primary asset (SPY) is held with weight=1 only in months
when it is the top-ranked (highest trailing 6-month return) of the three,
0 otherwise.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_basket_monthly_returns(index: pd.DatetimeIndex, lookback_months: int) -> pd.DataFrame:
    """Load TLT/GLD via data/loaders.py, compute month-end trailing
    lookback_months total returns, aligned to a monthly index."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = (index.min() - pd.Timedelta(days=lookback_months * 32)).to_pydatetime()
    end = (index.max() + pd.Timedelta(days=10)).to_pydatetime()

    out = {}
    for sym in ("TLT", "GLD"):
        df = load_equity(sym, start, end)
        close = df.set_index("timestamp")["close"] if "timestamp" in df.columns else df["close"]
        close.index = pd.to_datetime(close.index).tz_localize(None)
        monthly_close = close.resample("ME").last()
        monthly_ret = monthly_close.pct_change(lookback_months)
        out[sym] = monthly_ret
    return pd.DataFrame(out)


def generate_signals(
    price_df: pd.DataFrame,
    lookback_months: int = 6,
) -> pd.Series:
    """Return a {0,1} position series for the primary asset (intended to be
    SPY): 1 in months where the primary asset's trailing lookback_months
    return is the STRICT MAXIMUM among {primary, TLT, GLD}; 0 otherwise.
    Decision made at month-end close, applied to the FOLLOWING month
    (shift by one period) to avoid look-ahead, broadcast to daily bars.
    """
    df = _prep(price_df)
    close = df["close"]

    close_naive = close.copy()
    close_naive.index = pd.to_datetime(close_naive.index).tz_localize(None)
    monthly_close = close_naive.resample("ME").last()
    primary_ret = monthly_close.pct_change(lookback_months)

    basket = _load_basket_monthly_returns(close.index, lookback_months)
    basket = basket.reindex(primary_ret.index)

    combined = basket.copy()
    combined["PRIMARY"] = primary_ret

    is_winner = combined.idxmax(axis=1, skipna=True) == "PRIMARY"
    # Rows with any NaN in the comparison set are treated as not-a-winner
    # (insufficient warm-up history).
    valid = combined.notna().all(axis=1)
    is_winner = (is_winner & valid).astype(int)

    monthly_position_shifted = is_winner.shift(1).fillna(0).astype(int)

    # Reindex onto the daily index via its timezone-naive counterpart (the
    # monthly basket/primary series are computed tz-naive above), then
    # reattach the original (possibly tz-aware) daily index.
    daily_index_naive = pd.to_datetime(close.index).tz_localize(None)
    position = monthly_position_shifted.reindex(daily_index_naive, method="ffill").fillna(0).astype(int)
    position.index = close.index
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
