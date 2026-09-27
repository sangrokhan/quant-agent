"""Strategy: Continuous exposure-sizing dial driven by the AVERAGE of three
crypto-proxy ratio z-scores (GBTC/BTC, ETHE/ETH, MSTR/BTC), within an
SMA trend-following uptrend gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
This cron trigger's prior two iterations (2026-09-27-097 AND-of-2 gate;
2026-09-27-099 majority-vote gate) both used the three crypto-trust-proxy
ratio z-scores (GBTC/BTC, ETHE/ETH, MSTR/BTC) as BINARY stress flags
combined into a discrete gate (all-must-agree, or 2-of-3 vote). This
strategy follows this repo's established "binary-threshold-to-continuous-
sizing-dial rescue pattern" (already validated for VHF, CBOE SKEW, DPO,
Hurst, TII, RVI, MAMA-FAMA spread, Kalman slope, and others): instead of a
discrete stress flag, the MEAN of the three z-scores is tanh-squashed into
a smooth [0,1] exposure multiplier -- deeply negative average z-score
(broad crypto-trust discount stress) continuously scales exposure DOWN
rather than flipping fully flat/long at a discrete threshold, while an
SMA(trend_window) uptrend gate still determines the base long/flat
direction. This should reduce whipsaw at the binary threshold boundary
(a common failure mode already documented in this repo for many binary-
gate constructions) while preserving the underlying stress signal's
economic content.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def _ratio_zscore(a: pd.Series, b: pd.Series, zscore_window: int) -> pd.Series:
    merged = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    ratio = merged["a"] / merged["b"]
    roll_mean = ratio.rolling(zscore_window).mean()
    roll_std = ratio.rolling(zscore_window).std()
    zscore = (ratio - roll_mean) / roll_std.replace(0, float("nan"))
    return zscore


def _avg_proxy_zscore(index: pd.DatetimeIndex, zscore_window: int) -> pd.Series:
    from loaders import load_equity, load_crypto

    start = index.min() - pd.Timedelta(days=zscore_window * 3 + 30)
    end = index.max() + pd.Timedelta(days=5)

    gbtc = _prep(load_equity("GBTC", start.to_pydatetime(), end.to_pydatetime(), interval="1d"))["close"]
    ethe = _prep(load_equity("ETHE", start.to_pydatetime(), end.to_pydatetime(), interval="1d"))["close"]
    mstr = _prep(load_equity("MSTR", start.to_pydatetime(), end.to_pydatetime(), interval="1d"))["close"]
    btc = _prep(load_crypto("BTC/USDT", start.to_pydatetime(), end.to_pydatetime(), interval="1d"))["close"]
    eth = _prep(load_crypto("ETH/USDT", start.to_pydatetime(), end.to_pydatetime(), interval="1d"))["close"]

    gbtc_z = _ratio_zscore(gbtc, btc, zscore_window)
    ethe_z = _ratio_zscore(ethe, eth, zscore_window)
    mstr_z = _ratio_zscore(mstr, btc, zscore_window)

    avg_z = pd.concat([gbtc_z, ethe_z, mstr_z], axis=1).mean(axis=1)
    avg_z = avg_z.reindex(index, method="ffill")
    return avg_z


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    zscore_window: int = 90,
    sizing_scale: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous [0,1]-scaled exposure series (not strictly
    binary, but the validators/grid_test framework treats this as the
    'position' -- consistent with this repo's other continuous-sizing-dial
    strategies, which also return a non-binary weight from generate_signals).
    """
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    uptrend = close > sma

    avg_z = _avg_proxy_zscore(close.index, zscore_window)

    # tanh-squash: avg_z=0 -> full exposure (1.0); very negative avg_z -> 0.
    # sizing_scale controls how quickly exposure decays as avg_z goes negative.
    raw_dial = (np.tanh(avg_z.clip(upper=0) * sizing_scale) + 1.0).clip(0.0, 1.0)

    # Apply a deadband: only adjust exposure away from 1.0 once |dial-1| > deadband,
    # to reduce constant tiny position-size churn.
    dial = raw_dial.where((1.0 - raw_dial) > deadband, 1.0)

    exposure = np.where(uptrend, dial.fillna(1.0), 0.0)
    exposure = pd.Series(exposure, index=close.index)

    signal = exposure.shift(1).fillna(0.0)
    return signal


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    zscore_window: int = 90,
    sizing_scale: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Daily strategy returns, position-weighted, no transaction costs."""
    df = _prep(price_df)
    close = df["close"]
    positions = generate_signals(
        price_df,
        trend_window=trend_window,
        zscore_window=zscore_window,
        sizing_scale=sizing_scale,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = positions * daily_ret
    return strat_ret.fillna(0.0)
