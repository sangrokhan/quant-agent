"""Strategy: Dow Theory Confirmation + Low-Vol Regime Gate (direct fix attempt).

Direct fix for 2026-09-11-051 (Dow Theory Industrials/Transports new-high
confirmation, REJECTED -- decisive full-sample Sharpe/MDD failure despite
the grid showing the edge concentrated entirely in low-vol regimes: 100%
grid-cell pass rate in low-vol tercile vs 0% in high-vol tercile). This
strategy adds an explicit ex-ante volatility-regime gate -- following this
repo's own established fix pattern (2026-09-03-021: SMA golden-cross gated
by trailing realized-vol percentile <=0.5) and general trend-following
literature on regime filtering (per Google AI-overview synthesis of
"Volatility Regimes Explained" / "3.6 Volatility Regimes and Strategy
Survival" articles, which describe gating trend signals to only fire when
current realized volatility is below its own trailing historical
percentile) -- to keep the Dow Theory confirmation strategy in the regime
where 2026-09-11-051's own grid data showed it actually works, rather than
letting it trade (and lose) through high-vol regimes.

Signal logic
------------
- Same Dow Theory dual-confirmation core as 2026-09-11-051: primary asset
  makes a fresh N-day high AND confirming asset (IYT for equity, ETH for
  crypto) also made a fresh N-day high within a short lag window -> go
  long; symmetric new-low confirmation -> go flat.
- NEW: additionally require current realized volatility (trailing
  `vol_window`-day std of daily returns) to be at/below its own trailing
  `vol_lookback`-day percentile rank of `vol_percentile_threshold` (causal,
  no lookahead) before honoring a NEW long entry. Existing long positions
  are NOT force-exited purely by a vol-regime flip (only the Dow Theory
  new-low confirmation exits) -- the gate only suppresses fresh entries
  during elevated-vol regimes, consistent with 2026-09-03-021's own design.
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

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
    confirm_lag_days: int = 3,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_percentile_threshold: float = 0.5,
    is_crypto: bool = False,
) -> pd.Series:
    """Return a {0,1} long/flat position series: Dow Theory confirmation gated by low-vol regime."""
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

    # Causal realized-vol percentile regime gate.
    daily_ret = close.pct_change()
    realized_vol = daily_ret.rolling(vol_window, min_periods=max(2, vol_window // 2)).std()
    vol_percentile = realized_vol.rolling(vol_lookback, min_periods=max(20, vol_lookback // 4)).apply(
        lambda x: (x <= x.iloc[-1]).mean() if len(x) > 0 else 0.5, raw=False
    )
    low_vol_regime = (vol_percentile <= vol_percentile_threshold).fillna(False)

    bullish_confirm = primary_new_high & confirm_new_high_recent & low_vol_regime
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
