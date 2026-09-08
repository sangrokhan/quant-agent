"""Strategy: Kase Peak Oscillator (KPO) zero-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-057):
Cynthia Kase's Peak Oscillator (via Mladen's MQL4 port on the ProRealCode
forum, https://www.prorealcode.com/topic/kase-peak-oscillator-kase-cd-and-
kase-permission/, itself crediting the Forex TSD forum) measures the ratio
of the maximum recent directional move (over a short..long cycle band) to a
volatility-normalizer (a 30-period SMA of the 9-period stdev of log
returns), taking the "up" leg minus the "down" leg. Unlike RSI/Stochastic
which normalize by a fixed lookback, KPO's volatility-normalized max-move
construction is explicitly designed (per Kase's own "Two Faces of Momentum"
methodology) to spot momentum turning points across different volatility
regimes. First Kase Peak Oscillator strategy in this repo -- distinct from
every other momentum/oscillator family already tested (RSI, Stochastic,
CCI, CMO, RVI, TSI, Ultimate Oscillator, WaveTrend, Ergodic, SMI) via its
volatility-normalized max-directional-move construction rather than a
fixed-window average-gain/loss or close-position ratio.

Signal logic
------------
- Compute daily log returns; ccDev = rolling 9-day stdev of log returns;
  avg = rolling 30-day SMA of ccDev (volatility normalizer).
- For each day, over k in [short_cycle, long_cycle):
    up_leg  = max_k( log(High[t] / Low[t-k]) / sqrt(k) )   (recent high vs older low)
    down_leg= max_k( log(High[t-k] / Low[t]) / sqrt(k) )   (older high vs recent low)
  both divided by `avg`.
- xp = sensitivity * (SMA3(up_leg) - SMA3(down_leg))  -- this is KPO itself.
- Entry (long): KPO crosses above 0 (bullish momentum turn per source's own
  basic directional read of the oscillator).
- Exit: KPO crosses back below 0, or a max_hold_days time-stop (source's
  own peak/turning-point framing implies mean-reverting momentum bursts,
  not indefinite holds).
- Flat (no position) whenever not in an active long.

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5/6):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _kpo(
    df: pd.DataFrame,
    short_cycle: int = 8,
    long_cycle: int = 65,
    sensitivity: float = 40.0,
    dev_window: int = 9,
    avg_window: int = 30,
    smooth: int = 3,
) -> pd.Series:
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    n = len(df)

    log_ret = np.full(n, np.nan)
    log_ret[1:] = np.log(close[1:] / close[:-1], where=(close[1:] > 0) & (close[:-1] > 0),
                          out=np.full(n - 1, np.nan))

    ret_series = pd.Series(log_ret, index=df.index)
    cc_dev = ret_series.rolling(dev_window).std()
    avg = cc_dev.rolling(avg_window).mean()

    up_leg = np.full(n, np.nan)
    down_leg = np.full(n, np.nan)

    log_high = np.log(np.where(high > 0, high, np.nan))
    log_low = np.log(np.where(low > 0, low, np.nan))

    ks = np.arange(short_cycle, long_cycle)
    sqrt_k = np.sqrt(ks)

    for t in range(long_cycle, n):
        # up_leg: log(High[t]/Low[t-k]) / sqrt(k), max over k
        hh = log_high[t]
        lows_back = log_low[t - ks]
        up_vals = (hh - lows_back) / sqrt_k
        up_leg[t] = np.nanmax(up_vals)

        # down_leg: log(High[t-k]/Low[t]) / sqrt(k), max over k
        ll = log_low[t]
        highs_back = log_high[t - ks]
        down_vals = (highs_back - ll) / sqrt_k
        down_leg[t] = np.nanmax(down_vals)

    up_leg_s = pd.Series(up_leg, index=df.index) / avg
    down_leg_s = pd.Series(down_leg, index=df.index) / avg

    up_smooth = up_leg_s.rolling(smooth).mean()
    down_smooth = down_leg_s.rolling(smooth).mean()

    kpo = sensitivity * (up_smooth - down_smooth)
    return kpo


def generate_signals(
    price_df: pd.DataFrame,
    short_cycle: int = 8,
    long_cycle: int = 65,
    sensitivity: float = 40.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    kpo = _kpo(df, short_cycle=short_cycle, long_cycle=long_cycle, sensitivity=sensitivity)

    cross_up = (kpo > 0) & (kpo.shift(1) <= 0)
    cross_down = (kpo < 0) & (kpo.shift(1) >= 0)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = -1
    idx = df.index

    cross_up_arr = cross_up.to_numpy()
    cross_down_arr = cross_down.to_numpy()
    pos_arr = np.zeros(len(df), dtype=int)

    for i in range(len(df)):
        if in_pos:
            held = i - entry_idx
            if cross_down_arr[i] or held >= max_hold_days:
                in_pos = False
            else:
                pos_arr[i] = 1
        if not in_pos and cross_up_arr[i]:
            in_pos = True
            entry_idx = i
            pos_arr[i] = 1

    position = pd.Series(pos_arr, index=idx, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    short_cycle: int = 8,
    long_cycle: int = 65,
    sensitivity: float = 40.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        short_cycle=short_cycle,
        long_cycle=long_cycle,
        sensitivity=sensitivity,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change()
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns = strat_returns.fillna(0.0)
    return strat_returns
