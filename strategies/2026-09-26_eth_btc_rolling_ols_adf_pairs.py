"""Strategy: ETH/BTC rolling-OLS hedge-ratio + ADF-gated z-score pairs trade.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-26-031):
Read via browser_exec (github.com/Bauch0430/crypto-pairs-trading-btc-eth,
"Statistical Arbitrage: BTC/ETH Cointegration Pairs Trading Strategy",
web_extract's DDGS backend cannot extract GitHub URL content so the
README was read directly in a rendered browser). Source's own 1h-bar,
2021-2025 backtest methodology:
  1. Rolling OLS hedge ratio beta_t = OLS(ln(BTC) ~ ln(ETH)) over a
     trailing window W, SHIFTED by one period to prevent look-ahead.
  2. Spread_t = ln(BTC_t) - beta_t * ln(ETH_t).
  3. Augmented Dickey-Fuller (ADF) test on the trailing spread window;
     only trade when the rolling ADF p-value < 0.05 (cointegration-gate --
     source found the pair is stationary only ~9.8% of hours, so gating
     out non-stationary regimes is central to the strategy, not optional).
  4. Rolling z-score of the spread (mean/std over the same trailing
     window, shifted to avoid look-ahead).
  5. Entry when |z| > entry_z AND ADF p-value < adf_threshold; exit on
     take-profit (|z| < exit_z), stop-loss (|z| > stop_z), or a time-stop
     (holding_bars > max_hold_days).

This repo's strategy interface returns ONE return series (no dedicated
short-leg P&L), so -- consistent with this repo's other pairs-trade
entries (2026-09-04-083 ETH/BTC spread z-score, 2026-09-10-023 GDX/RING,
2026-09-22-036 UNG/USO) -- we approximate the "long the cheap leg" side
only: long ETH (this file's own `price_df` asset) when z < -entry_z (BTC
rich / ETH cheap relative to the fitted hedge ratio) AND the ADF gate
passes, flat otherwise. This is a genuinely NEW construction distinct
from 2026-09-04-083 (which used a naive FIXED 1:1 log-ratio spread with
no fitted hedge ratio and no cointegration/ADF gate at all, and was
rejected) -- this version adds (a) a time-varying rolling-OLS-fitted
hedge ratio instead of an assumed 1:1 ratio, and (b) the ADF stationarity
gate the source's own research explicitly found necessary (only ~9.8% of
windows are actually cointegrated) to filter out structural-break regimes
where the naive spread would diverge without reverting.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
        price_df is expected to be the ETH/USDT OHLCV frame; the BTC leg
        is fetched internally via data/loaders.py (load_crypto).
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_btc_series(index: pd.Index) -> pd.Series:
    """Fetch BTC/USDT close series aligned to the given index, via data/loaders.py."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_crypto  # noqa: E402

    start = index.min()
    end = index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None) if hasattr(start, "tz_localize") else start.replace(tzinfo=None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None) if hasattr(end, "tz_localize") else end.replace(tzinfo=None)
    btc_df = load_crypto("BTC/USDT", start=start, end=end, interval="1d")
    btc_df = _prep(btc_df)
    return btc_df["close"].reindex(index).ffill()


def _rolling_ols_beta(y: pd.Series, x: pd.Series, window: int) -> pd.Series:
    """Rolling OLS slope of y ~ x (no intercept subtracted from means:
    standard beta = cov(x,y)/var(x)), shifted by 1 to avoid look-ahead."""
    x_mean = x.rolling(window).mean()
    y_mean = y.rolling(window).mean()
    cov = (x * y).rolling(window).mean() - x_mean * y_mean
    var = (x * x).rolling(window).mean() - x_mean * x_mean
    beta = (cov / var.replace(0, np.nan)).shift(1)
    return beta


def _rolling_adf_pvalues(spread: pd.Series, window: int, step: int = 5) -> pd.Series:
    """Rolling ADF p-value on the trailing `window` of `spread`, recomputed
    every `step` bars (forward-filled between) to keep runtime tractable
    over a multi-year daily-bar sample -- the ADF test itself is only
    evaluated on data STRICTLY BEFORE the current bar (shifted by 1)."""
    import warnings

    from statsmodels.tsa.stattools import adfuller

    vals = spread.to_numpy()
    n = len(vals)
    pvals = np.full(n, np.nan)
    i = window
    while i < n:
        window_data = vals[i - window : i]  # strictly prior to bar i -> assigned at i (no look-ahead)
        if np.all(np.isfinite(window_data)) and np.std(window_data) > 1e-12:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", FutureWarning)
                    pvals[i] = adfuller(window_data, maxlag=1, autolag=None)[1]
            except Exception:
                pvals[i] = np.nan
        i += step
    series = pd.Series(pvals, index=spread.index)
    return series.ffill()


def _compute_signal_frame(price_df: pd.DataFrame, window: int, adf_step: int) -> pd.DataFrame:
    df = _prep(price_df)
    close_eth = df["close"]
    close_btc = _get_btc_series(df.index)
    log_eth = np.log(close_eth)
    log_btc = np.log(close_btc)

    beta = _rolling_ols_beta(log_btc, log_eth, window)
    spread = log_btc - beta * log_eth

    rolling_mean = spread.rolling(window).mean().shift(1)
    rolling_std = spread.rolling(window).std().shift(1)
    z = (spread - rolling_mean) / rolling_std.replace(0, np.nan)

    adf_p = _rolling_adf_pvalues(spread, window, step=adf_step)

    out = pd.DataFrame({"z": z, "adf_p": adf_p}, index=df.index)
    return out


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 60,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    stop_z: float = 4.0,
    adf_threshold: float = 0.05,
    adf_step: int = 5,
    max_hold_days: int = 45,
) -> pd.Series:
    """Return a {0,1} long/flat position series (long-ETH-leg approximation
    of the BTC-rich/ETH-cheap side of the pairs trade, gated by rolling
    ADF cointegration test on the fitted spread)."""
    df = _prep(price_df)
    sig = _compute_signal_frame(df, window, adf_step)
    z = sig["z"]
    adf_p = sig["adf_p"]
    z_prev = z.shift(1)

    cointegrated = adf_p < adf_threshold
    entry_trigger = (z < -entry_z) & (z_prev >= -entry_z) & cointegrated.fillna(False)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    z_vals = z.to_numpy()
    entry_vals = entry_trigger.to_numpy()
    pos_vals = np.zeros(n, dtype=int)
    for i in range(n):
        zi = z_vals[i]
        if in_pos:
            hold_count += 1
            reverted = (zi >= -exit_z) if np.isfinite(zi) else False
            stopped = (abs(zi) >= stop_z) if np.isfinite(zi) else False
            if reverted or stopped or hold_count >= max_hold_days:
                in_pos = False
                pos_vals[i] = 0
            else:
                pos_vals[i] = 1
        else:
            if bool(entry_vals[i]):
                in_pos = True
                hold_count = 0
                pos_vals[i] = 1
            else:
                pos_vals[i] = 0
    position = pd.Series(pos_vals, index=df.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    window: int = 60,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    stop_z: float = 4.0,
    adf_threshold: float = 0.05,
    adf_step: int = 5,
    max_hold_days: int = 45,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's ETH simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        window=window,
        entry_z=entry_z,
        exit_z=exit_z,
        stop_z=stop_z,
        adf_threshold=adf_threshold,
        adf_step=adf_step,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
