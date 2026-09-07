"""Strategy: Garman-Klass vol-squeeze breakout + low/mid-vol regime gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-044):
Direct follow-up to the near-miss Garman-Klass volatility-compression
breakout strategy already in this repo (id=2026-09-08-023,
strategies/2026-09-08_garman_klass_vol_squeeze_breakout.py): full-sample
Sharpe 0.80 (near-miss), grid pass_fraction 8/72 with the repo's own
recorded note that passing cells were "low/mid-vol-concentrated" (i.e.
the edge, where present, avoided the high-vol tercile). This repo's
established, previously-productive fix pattern (KAMA/ATR-band
2026-09-06-183, Elder-Ray Bull Power 2026-09-06-176) is to add an
explicit realized-volatility regime gate on top of an unchanged base
entry/exit signal, restricting entries to the regime(s) where the edge
was already concentrated -- here, low OR mid vol (excluding high-vol,
unlike the single-tercile low-vol-only gates used in those precedents,
since this base strategy's own grid pass distribution spanned BOTH low
and mid, not just low).

Identical Garman-Klass compression-breakout entry/exit logic to the base
strategy is kept unchanged; only a realized-vol regime gate (20d realized
vol NOT in the top vol_exclude_pct percentile of its own trailing 1yr
window, i.e. excluding the high-vol tail) is added on top of the entry
condition, testing whether excluding the strategy's own worst-performing
regime alone rescues the near-miss full-sample Sharpe above 1.0.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py).
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


def _garman_klass_vol(df: pd.DataFrame, gk_window: int) -> pd.Series:
    high, low, open_, close = df["high"], df["low"], df["open"], df["close"]
    log_hl = np.log(high / low)
    log_co = np.log(close / open_)
    gk_var_per_bar = 0.5 * (log_hl ** 2) - (2 * np.log(2) - 1) * (log_co ** 2)
    gk_var_mean = gk_var_per_bar.rolling(gk_window).mean().clip(lower=0)
    return np.sqrt(gk_var_mean * 252)


def _percentile_rank(series: pd.Series, lookback: int) -> pd.Series:
    def _rank(window: np.ndarray) -> float:
        last = window[-1]
        return float((window <= last).sum()) / len(window) * 100.0

    return series.rolling(lookback).apply(_rank, raw=True)


def _not_high_vol_regime(close: pd.Series, vol_window: int, lookback: int, vol_exclude_pct: float) -> pd.Series:
    """True unless current realized vol is in the top vol_exclude_pct
    percentile of its own trailing `lookback`-bar window (excludes the
    high-vol tail only, keeps low AND mid)."""
    daily_ret = close.pct_change()
    realized_vol = daily_ret.rolling(vol_window).std()
    pct_rank = _percentile_rank(realized_vol, lookback)
    return (pct_rank <= (100.0 - vol_exclude_pct)).fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    gk_window: int = 20,
    pct_lookback: int = 100,
    squeeze_pct: float = 20.0,
    expand_pct: float = 80.0,
    breakout_window: int = 20,
    trend_window: int = 100,
    max_hold_days: int = 10,
    vol_window: int = 20,
    vol_regime_lookback: int = 252,
    vol_exclude_pct: float = 33.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    gk_vol = _garman_klass_vol(df, gk_window)
    pct_rank = _percentile_rank(gk_vol, pct_lookback)

    squeeze_prior = (pct_rank.shift(1) <= squeeze_pct)
    prior_high = high.shift(1).rolling(breakout_window).max()
    breakout = close > prior_high

    trend_sma = close.rolling(trend_window, min_periods=trend_window // 2).mean()
    uptrend = close > trend_sma

    not_high_vol = _not_high_vol_regime(close, vol_window, vol_regime_lookback, vol_exclude_pct)

    entry = (
        squeeze_prior.fillna(False)
        & breakout.fillna(False)
        & uptrend.fillna(False)
        & not_high_vol
    )
    exit_expand = pct_rank > expand_pct
    exit_trend_break = ~uptrend.fillna(False)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_expand.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
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
