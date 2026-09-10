"""Strategy: Yang-Zhang OHLC volatility estimator as a calm-regime gate for
an SMA trend-following signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id, this iteration):
Per LuxAlgo's Yang-Zhang Estimator documentation (visited this iteration):
the Yang-Zhang estimator combines overnight (close-to-open) log-return
variance, open-to-close variance, and a Rogers-Satchell range term into a
single OHLC-based realized-volatility measure that (unlike close-to-close
estimators) properly accounts for both opening gaps and price drift. The
source's own disclosed trading use: "Expansion/contraction: the primary
[fast] estimate crossing above the slower comparison estimate signals
volatility expanding; crossing below, contracting... It is a sizing and
regime instrument, not a directional signal."

This strategy operationalizes that explicit regime-instrument framing:
trade a simple SMA trend-following signal (close crossing above its own
trend SMA) ONLY when the Yang-Zhang volatility regime is CONTRACTING (fast
window estimate <= slow window estimate, i.e. realized vol is calm/falling
rather than expanding), on the premise that trend-following works better
in genuinely calm-and-drifting conditions than in expanding-volatility
regimes where whipsaws are more likely. This is structurally distinct from
this repo's already-tested Garman-Klass percentile-rank compression
BREAKOUT strategy (2026-09-08-023/044, which fires on breakout AT THE
MOMENT vol expands out of a squeeze) and from the Parkinson
expansion-cross/compression-mean-reversion pair (2026-09-09-027/028): here
the Yang-Zhang fast/slow relationship is used purely as an ongoing
regime GATE for a separate, independent trend-following entry signal, not
as the entry trigger itself.

Signal logic
------------
- Yang-Zhang annualized volatility computed over a fast window (default 20
  bars) and a slow comparison window (default 60 bars), per LuxAlgo's
  disclosed formula: overnight variance + k * open-to-close variance +
  (1-k) * Rogers-Satchell variance, with k = 0.34 / (1.34 + (n+1)/(n-1)).
- Calm regime: fast_YZ <= slow_YZ (volatility contracting/stable, not
  expanding).
- Entry (long): close crosses above SMA(trend_window) AND we are in the
  calm regime.
- Exit: close crosses back below SMA(trend_window), OR the regime flips to
  expanding (fast_YZ > slow_YZ, risk-off exit), OR a max_hold_days
  time-stop.
- Flat (no position) whenever not in an active long.

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
    return df


def _yang_zhang_vol(df: pd.DataFrame, window: int, periods_per_year: int = 252) -> pd.Series:
    """Annualized Yang-Zhang OHLC realized volatility over a rolling window."""
    o = df["open"]
    h = df["high"]
    l = df["low"]
    c = df["close"]
    c_prev = c.shift(1)

    overnight = np.log(o / c_prev)
    open_to_close = np.log(c / o)
    rs = np.log(h / c) * np.log(h / o) + np.log(l / c) * np.log(l / o)

    overnight_var = overnight.rolling(window).var(ddof=1)
    oc_var = open_to_close.rolling(window).var(ddof=1)
    rs_var = rs.rolling(window).mean()

    n = window
    k = 0.34 / (1.34 + (n + 1) / (n - 1))

    yz_var = overnight_var + k * oc_var + (1 - k) * rs_var
    yz_vol = np.sqrt(yz_var.clip(lower=0.0)) * (periods_per_year ** 0.5)
    return yz_vol


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 60,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_yz = _yang_zhang_vol(df, fast_window)
    slow_yz = _yang_zhang_vol(df, slow_window)
    calm_regime = (fast_yz <= slow_yz).fillna(False)

    sma_trend = close.rolling(trend_window).mean()
    trend_entry_cross = (close.shift(1) <= sma_trend.shift(1)) & (close > sma_trend)
    trend_exit_cross = (close.shift(1) >= sma_trend.shift(1)) & (close < sma_trend)

    entry = trend_entry_cross & calm_regime

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            expanding = not bool(calm_regime.iloc[i])
            if bool(trend_exit_cross.iloc[i]) or expanding or held >= max_hold_days:
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
