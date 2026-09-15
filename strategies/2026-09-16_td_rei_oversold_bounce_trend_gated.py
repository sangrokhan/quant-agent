"""Strategy: TD REI (DeMark Range Expansion Index) oversold-bounce, trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Thomas DeMark's Range Expansion Index (TD REI, 1994) is an arithmetically-
calculated momentum oscillator (range -100..+100) that compares the current
bar's high/low displacement against 5/6-bar-ago and 2-bar-vs-7/8-bar-ago
reference points, normalized by the sum of absolute displacements over a
lookback window N. Per the exact disclosed formula (linnsoft.com/Investor-RT
RTL transcription):

    condition = (HI>=LO[5] OR HI>=LO[6]) AND (LO<=HI[5] OR LO<=HI[6])
             OR (HI[2]>=CL[7] OR HI[2]>=CL[8]) AND (LO[2]<=CL[7] OR LO[2]<=CL[8])
    if condition: VALUE = HI - HI[2] + LO - LO[2]
                  ABSVALUE = |HI - HI[2]| + |LO - LO[2]|
    else:         VALUE = ABSVALUE = 0
    TD_REI = 100 * SUM(VALUE, N) / SUM(ABSVALUE, N)

DeMark's own overbought/oversold convention (per enlightenedstocktrading.com,
matching the more commonly-cited +/-60 threshold): a long entry follows REI
crossing below -60 (oversold) and then turning back up (rising), signaling
an oversold bounce; symmetric short entry not used here (long-only per this
repo's contract). To avoid fighting decisive downtrends (a documented risk
-- the source's own QQQ backtest example carried a 49% max drawdown with no
trend filter), this repo's established trend-gate pattern (close above a
trailing SMA) is added on top of the raw DeMark entry/exit rule -- first REI
strategy in this repo, distinct from every other oscillator threshold-cross
already tested (RSI, CMO, Stochastic, Williams %R, etc.) via its unique
true-high/low-displacement-ratio construction, not a close-based formula.

Signal logic
------------
- Long (position=1) entry: REI crossed below oversold_threshold (default
  -60) within the last `lookback_confirm` bars, REI has now turned up
  (REI_t > REI_{t-1}), AND close is above SMA(trend_window) (trend gate).
- Exit: REI rises above exit_threshold (default 0, i.e. back to neutral or
  higher), the trend filter breaks (close < SMA), or a max_hold_days cap.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _compute_rei(high: pd.Series, low: pd.Series, close: pd.Series, n: int) -> pd.Series:
    hi2 = high.shift(2)
    lo2 = low.shift(2)
    lo5 = low.shift(5)
    lo6 = low.shift(6)
    hi5 = high.shift(5)
    hi6 = high.shift(6)
    cl7 = close.shift(7)
    cl8 = close.shift(8)

    cond_a = ((high >= lo5) | (high >= lo6)) & ((low <= hi5) | (low <= hi6))
    cond_b = ((hi2 >= cl7) | (hi2 >= cl8)) & ((lo2 <= cl7) | (lo2 <= cl8))
    condition = (cond_a | cond_b).fillna(False)

    value = (high - hi2 + low - lo2).where(condition, 0.0)
    absvalue = ((high - hi2).abs() + (low - lo2).abs()).where(condition, 0.0)

    sum_value = value.rolling(n).sum()
    sum_absvalue = absvalue.rolling(n).sum()
    rei = 100.0 * sum_value / sum_absvalue.replace(0.0, np.nan)
    return rei.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    rei_period: int = 8,
    oversold_threshold: float = -60.0,
    exit_threshold: float = 0.0,
    lookback_confirm: int = 5,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series from the REI oversold-bounce rule."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    rei = _compute_rei(high, low, close, rei_period)
    rei_rising = rei > rei.shift(1)
    was_oversold_recently = (rei < oversold_threshold).rolling(lookback_confirm).max().astype(bool)

    sma_trend = close.rolling(trend_window).mean()
    trend_ok = close > sma_trend

    entry = was_oversold_recently & rei_rising & trend_ok
    exit_ = (rei > exit_threshold) | (~trend_ok)

    n = len(df)
    pos = np.zeros(n, dtype=int)
    in_pos = False
    hold = 0
    entry_arr = entry.to_numpy()
    exit_arr = exit_.to_numpy()
    for i in range(n):
        if in_pos:
            hold += 1
            if exit_arr[i] or hold > max_hold_days:
                in_pos = False
                hold = 0
            else:
                pos[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold = 1
                pos[i] = 1
    return pd.Series(pos, index=df.index)


def generate_returns(
    price_df: pd.DataFrame,
    rei_period: int = 8,
    oversold_threshold: float = -60.0,
    exit_threshold: float = 0.0,
    lookback_confirm: int = 5,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        rei_period=rei_period,
        oversold_threshold=oversold_threshold,
        exit_threshold=exit_threshold,
        lookback_confirm=lookback_confirm,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    return position.shift(1).fillna(0) * daily_ret
