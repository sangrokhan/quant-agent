"""Strategy: Dow Theory Industrials/Transports New-High Confirmation.

Hypothesis (2026-09-11-051): per StockCharts ChartSchool's Dow Theory
article (https://chartschool.stockcharts.com/table-of-contents/market-
analysis/dow-theory), a primary bull-trend signal is only considered valid
when BOTH the Industrial Average and the Rail/Transportation Average
confirm each other by recording new highs close together in time; a
non-confirmation (one index making a new high/low without the other
following) is a warning sign. This strategy operationalizes that rule on
single tickers rather than the classic indices: the traded asset (e.g. QQQ
or SPY, playing the "Industrials" role) generates a bullish signal only
when it makes a fresh N-day high AND a confirming asset (IYT, the iShares
Transportation ETF, playing the "Transports" role) also makes its own
fresh N-day high within a short confirmation lag window. Symmetric logic
exits/flips flat on a joint new-N-day-low confirmation. For crypto, ETH is
used as the "confirming" leg against BTC as a falsification check (no
analogous industrial/transport sector split exists in crypto, so a genuine
edge here would be surprising).

Signal logic
------------
- primary_new_high = close makes a new `lookback_window`-day high today.
- confirm_new_high = confirming asset's close made a new `lookback_window`
  -day high at any point in the trailing `confirm_lag_days` window.
- Bullish confirmation (go/stay long) when primary_new_high AND
  confirm_new_high both true within the lag window.
- Bearish confirmation (go/stay flat) on the symmetric joint new-low
  condition.
- Position holds its last confirmed state between confirmation events
  (ffill), starting flat.
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

# Confirming-asset ticker per traded-asset "family" (equity vs crypto).
_CONFIRM_TICKER = {
    "equity": "IYT",
    "crypto": "ETH/USDT",
}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _naive_index(idx):
    return idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx


def _get_confirm_series(idx: pd.DatetimeIndex, lookback_window: int, is_crypto: bool) -> pd.DataFrame:
    """Return confirm asset's new-high / new-low boolean series reindexed to idx."""
    if is_crypto:
        from loaders import load_crypto

        lookback_days = lookback_window * 2 + 30
        start = (idx.min() - pd.Timedelta(days=lookback_days)).to_pydatetime()
        end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()
        confirm_df = load_crypto(_CONFIRM_TICKER["crypto"], start, end, interval="1h")
        confirm_df = confirm_df.set_index("timestamp").sort_index()
        confirm_close = confirm_df["close"].resample("1D").last().dropna()
    else:
        from loaders import load_equity

        lookback_days = lookback_window * 2 + 30
        start = (idx.min() - pd.Timedelta(days=lookback_days)).to_pydatetime()
        end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()
        confirm_close = load_equity(_CONFIRM_TICKER["equity"], start, end).set_index("timestamp")["close"].sort_index()

    confirm_close.index = _naive_index(confirm_close.index)
    rolling_high = confirm_close.rolling(lookback_window, min_periods=lookback_window // 2).max()
    rolling_low = confirm_close.rolling(lookback_window, min_periods=lookback_window // 2).min()
    new_high = confirm_close >= rolling_high
    new_low = confirm_close <= rolling_low

    target_idx = _naive_index(idx)
    out = pd.DataFrame({"new_high": new_high, "new_low": new_low})
    out = out.reindex(out.index.union(target_idx)).sort_index().ffill()
    out = out.reindex(target_idx)
    out.index = idx
    return out.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    lookback_window: int = 50,
    confirm_lag_days: int = 5,
    is_crypto: bool = False,
) -> pd.Series:
    """Return a {0,1} long/flat position series per the Dow Theory confirmation rule."""
    df = _prep(price_df)
    idx = df.index
    close = df["close"]

    primary_high = close.rolling(lookback_window, min_periods=lookback_window // 2).max()
    primary_low = close.rolling(lookback_window, min_periods=lookback_window // 2).min()
    primary_new_high = close >= primary_high
    primary_new_low = close <= primary_low

    try:
        confirm = _get_confirm_series(idx, lookback_window, is_crypto)
        confirm_new_high_recent = confirm["new_high"].rolling(confirm_lag_days, min_periods=1).max().astype(bool)
        confirm_new_low_recent = confirm["new_low"].rolling(confirm_lag_days, min_periods=1).max().astype(bool)
    except Exception:
        confirm_new_high_recent = pd.Series(False, index=idx)
        confirm_new_low_recent = pd.Series(False, index=idx)

    bullish_confirm = primary_new_high & confirm_new_high_recent
    bearish_confirm = primary_new_low & confirm_new_low_recent

    state = pd.Series(index=idx, dtype=float)
    state[bullish_confirm] = 1.0
    state[bearish_confirm] = 0.0
    state = state.ffill().fillna(0.0)
    return state.astype(int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
