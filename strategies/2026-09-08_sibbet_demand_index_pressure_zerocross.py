"""Strategy: Demand Index (James Sibbet) volume-pressure zero-cross trend
strategy -- long only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-012):
Per the TradingView conair "Demand Index (James Sibbet)" script description
(https://www.tradingview.com/script/CY3t5FqX-Demand-Index-James-Sibbet/,
confirming Sibbet's original H+L+2C weighted price and 0.375 exponential
factor) and LuxAlgo's Demand Index library page
(https://www.luxalgo.com/library/indicator/demand-index/, confirming the
volume/volatility normalization and buy/sell pressure split mechanics),
Sibbet's Demand Index is a leading volume-price oscillator: volume
(normalized by its recent average) is split into buying vs. selling
pressure components according to the size and direction of a
volatility-scaled move in the weighted price (H+L+2C)/4; both pressure
components are EMA-smoothed and combined into a signed, zero-centered
ratio. LuxAlgo's own trading rule: "Cross above zero: buying pressure has
overtaken selling pressure" is the entry signal used here (Sibbet's own
"volume leads price" premise). This is a documented best-effort
reconstruction -- the exact original 20+-column 1986 Sibbet spreadsheet
formula (Stocks & Commodities, June 1986) is not freely available online
(Scribd PDF and Investopedia page both inaccessible this iteration); the
weighted-price input, exponential factor, and pressure-split/EMA-smoothing
mechanics are taken directly from the two sources above. First Demand
Index strategy in this repo -- distinct from all prior volume oscillators
(OBV, Klinger, Twiggs Money Flow, Ease of Movement, VPT, Chaikin Money
Flow) since Demand Index splits volume into signed pressure via a
volatility-scaled price-change term rather than a raw price-direction sign
or Money-Flow-Multiplier construction.

Signal logic
------------
- weighted_price = (High + Low + 2*Close) / 4.
- pct_change = weighted_price.pct_change() (volatility-scaled move).
- volatility = rolling std(pct_change, vol_window) (normalizer, avoids
  divide-by-zero / extreme spikes on tiny denominators).
- k = pct_change / volatility.clip(lower=eps) (dimensionless move size).
- vol_ratio = volume / rolling_mean(volume, vol_norm_window) (Sibbet's
  volume normalized by recent average).
- Buying pressure BP = vol_ratio where k > 0, else vol_ratio / (1 + exp_factor*|k|)
  (buying dominates on up-moves, scaled down on down-moves per the
  exponential-factor construction); Selling pressure SP is the mirror
  (dominates on down-moves).
- BP_smooth = EMA(BP, smooth_window); SP_smooth = EMA(SP, smooth_window).
- Demand Index DI = (BP_smooth - SP_smooth) / (BP_smooth + SP_smooth)
  (signed ratio in [-1, 1], zero-centered).
- Entry (long): DI crosses above 0 AND close > SMA(trend_window) (per
  Sibbet's own volume-leads-price premise, gated by a basic trend filter
  since a pure zero-cross alone is known to whipsaw -- consistent with
  every other zero-line-crossover oscillator already tested in this repo
  needing a trend filter to pass).
- Exit: DI crosses back below 0, OR close < SMA(trend_window), OR a
  max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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


def _compute_demand_index(
    df: pd.DataFrame,
    vol_window: int,
    vol_norm_window: int,
    smooth_window: int,
    exp_factor: float,
) -> pd.Series:
    high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]
    weighted_price = (high + low + 2.0 * close) / 4.0
    pct_change = weighted_price.pct_change()
    volatility = pct_change.rolling(vol_window, min_periods=vol_window).std()
    eps = 1e-8
    k = pct_change / volatility.clip(lower=eps)

    vol_avg = volume.rolling(vol_norm_window, min_periods=vol_norm_window).mean()
    vol_ratio = volume / vol_avg.replace(0, np.nan)

    k_abs = k.abs()
    damp = 1.0 / (1.0 + exp_factor * k_abs)

    bp = vol_ratio.where(k > 0, vol_ratio * damp)
    sp = vol_ratio.where(k < 0, vol_ratio * damp)

    bp_smooth = bp.ewm(span=smooth_window, adjust=False, min_periods=smooth_window).mean()
    sp_smooth = sp.ewm(span=smooth_window, adjust=False, min_periods=smooth_window).mean()

    denom = (bp_smooth + sp_smooth).replace(0, np.nan)
    demand_index = (bp_smooth - sp_smooth) / denom
    return demand_index


def generate_signals(
    price_df: pd.DataFrame,
    vol_window: int = 10,
    vol_norm_window: int = 10,
    smooth_window: int = 10,
    exp_factor: float = 0.375,
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    di = _compute_demand_index(df, vol_window, vol_norm_window, smooth_window, exp_factor)
    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()

    di_prev = di.shift(1)
    cross_up = (di > 0) & (di_prev <= 0)
    cross_down = (di < 0) & (di_prev >= 0)
    trend_ok = close > trend_sma

    entry = (cross_up & trend_ok).fillna(False)
    exit_signal = (cross_down | (~trend_ok)).fillna(False)

    n = len(df)
    entry_arr = entry.to_numpy()
    exit_arr = exit_signal.to_numpy()
    pos_arr = [0] * n

    in_pos = False
    hold_counter = 0
    for i in range(n):
        if in_pos:
            hold_counter += 1
            exit_now = bool(exit_arr[i]) or hold_counter >= max_hold_days
            if exit_now:
                in_pos = False
                hold_counter = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if bool(entry_arr[i]):
                in_pos = True
                hold_counter = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    vol_window: int = 10,
    vol_norm_window: int = 10,
    smooth_window: int = 10,
    exp_factor: float = 0.375,
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        vol_window=vol_window,
        vol_norm_window=vol_norm_window,
        smooth_window=smooth_window,
        exp_factor=exp_factor,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
