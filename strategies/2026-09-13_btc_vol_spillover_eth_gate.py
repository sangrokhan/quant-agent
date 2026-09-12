"""Strategy: BTC realized-volatility spike gates ETH trend-following (crypto
volatility SPILLOVER, distinct from return spillover).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-13-018):
Per https://aligrithm.com/crypto-isnt-structurally-alien-roll-vpin-amihud-predict-distribution-shifts/
(read via browser_exec this iteration), a critical re-analysis of Easley,
O'Hara, Yang & Zhang's crypto microstructure paper found that after
correcting for estimator artifacts, ONE finding survives a Bonferroni-
corrected robustness check: BTC and ETH's own Roll-measure (effectively a
volatility proxy) are the only cross-coin features with any feature
importance for predicting the SIGN of the next day's realized-volatility
CHANGE in smaller altcoins -- i.e. BTC/ETH volatility leads smaller-coin
volatility at roughly a one-day horizon. This is a VOLATILITY-spillover
finding, not a return-spillover one (this repo's 2026-09-11-105 already
tested and rejected BTC->ETH RETURN spillover; this is a different
mechanism).

Adapted single-instrument test (this repo's loaders only cover BTC/ETH, not
XRP/SOL/ADA, so we test the adjacent pair the paper itself flags as the
"leading" side: does BTC's OWN volatility spiking predict elevated ETH
volatility one day ahead, and does gating an ETH trend-following strategy to
go flat/reduce exposure right after a BTC vol spike improve risk-adjusted
returns by avoiding volatility expansion in ETH)?

Signal logic
------------
- Trend filter: ETH close > SMA(trend_window) (baseline trend-following).
- BTC vol-spike gate: BTC's own rolling realized volatility (btc_vol_window
  days) is compared to its trailing btc_vol_lookback-day historical
  distribution; if BTC's current realized vol is above the
  btc_vol_spike_percentile percentile of that trailing distribution, treat
  today as a "BTC vol spike" day -- per the paper's finding, ETH's own
  volatility is expected to expand over the next ~1 day, so the strategy
  goes FLAT for cooldown_days trading days following the spike (avoiding
  the anticipated elevated-vol regime), even if the trend filter says long.
- Otherwise: long/flat purely per the ETH trend filter.
- No shorting (SAFETY.md).

Interface contract for validators (see validation/validators.py) and the
grid tester (see validation/grid_test.py): both generate_signals and
generate_returns accept price_df (expected to be ETH/USDT) plus the
strategy's tunable parameters as keyword arguments; BTC/USDT data is
fetched internally via data/loaders.py.load_crypto (same pattern as
2026-09-08_silicon_vs_satoshi_donchian_rotation.py and
2026-09-13_gold_bitcoin_dual_momentum_voltarget.py).
"""

from __future__ import annotations

import sys
import os

import math

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_crypto  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _realized_vol(close: pd.Series, window: int) -> pd.Series:
    log_ret = (close / close.shift(1)).apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    return log_ret.rolling(window).std()


def _load_btc_close(start, end) -> pd.Series:
    df = load_crypto("BTC/USDT", start, end, interval="1d")
    df = _prep(df)
    return df["close"]


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    btc_vol_window: int = 10,
    btc_vol_lookback: int = 90,
    btc_vol_spike_percentile: float = 0.9,
    cooldown_days: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series for ETH, gated by a BTC
    realized-volatility spike cooldown."""
    df = _prep(price_df)
    close = df["close"]

    trend_sma = close.rolling(trend_window).mean()
    in_uptrend = (close > trend_sma).fillna(False)

    start = df.index.min()
    end = df.index.max()
    btc_close = _load_btc_close(start, end)
    btc_close = btc_close.reindex(close.index).ffill()

    btc_vol = _realized_vol(btc_close, btc_vol_window)
    btc_vol_pctile = btc_vol.rolling(btc_vol_lookback, min_periods=btc_vol_window).apply(
        lambda x: (x < x.iloc[-1]).mean() if len(x) > 0 else np.nan, raw=False
    )
    btc_vol_spike = (btc_vol_pctile >= btc_vol_spike_percentile).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    cooldown_remaining = 0
    spike_vals = btc_vol_spike.values
    uptrend_vals = in_uptrend.values

    for i in range(len(close)):
        if bool(spike_vals[i]):
            cooldown_remaining = cooldown_days
        if cooldown_remaining > 0:
            position.iloc[i] = 0
            cooldown_remaining -= 1
        else:
            position.iloc[i] = 1 if bool(uptrend_vals[i]) else 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    btc_vol_window: int = 10,
    btc_vol_lookback: int = 90,
    btc_vol_spike_percentile: float = 0.9,
    cooldown_days: int = 3,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        trend_window=trend_window,
        btc_vol_window=btc_vol_window,
        btc_vol_lookback=btc_vol_lookback,
        btc_vol_spike_percentile=btc_vol_spike_percentile,
        cooldown_days=cooldown_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = daily_ret * position.shift(1).fillna(0)
    return strat_returns
