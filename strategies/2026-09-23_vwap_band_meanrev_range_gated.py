"""Strategy: Rolling VWAP mean reversion with std-dev bands, range-regime gated.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id): per
Traders Journal's "VWAP Mean Reversion" strategy page
(https://tradersjournal.app/strategies/vwap-mean-reversion, read via
browser_exec this iteration), price fades back toward VWAP once it
stretches an unusual distance away, but only in a session/regime that is
actually range-bound (a trending regime keeps stretching, defeating the
reversion premise) -- the source's own stated failure mode #1 is "fading a
stretch during a trending session". The source frames this on intraday
VWAP with std-dev bands and a reversal-candle/momentum-stall confirmation,
targeting a return to VWAP with a stop just beyond the band.

Adaptation to this repo's daily-bar data: true session VWAP needs intraday
tick volume, unavailable here, so a rolling N-day volume-weighted average
price (VWAP proxy) is used instead, with volume-weighted std bands (2 std
default, matching the source's "first or second deviation band" framing
plus market convention). The source's own "confirm range-bound before
entering" rule is operationalized as ADX(14) < adx_threshold (25, standard
trend/no-trend cutoff) -- a numeric regime gate the source described only
qualitatively. The source's "momentum stalling" confirmation is
operationalized as a simple 1-bar close-up-tick after the band touch. This
is the first VWAP-band strategy in this repo (0 prior KB hits for "VWAP").

Signal logic
------------
- Rolling VWAP: sum(close*volume, vwap_window) / sum(volume, vwap_window).
- Rolling volume-weighted variance of close around that VWAP over the same
  window -> vw_std; lower_band = vwap - band_mult * vw_std.
- Range regime gate: ADX(adx_period) < adx_threshold (Wilder's ADX).
- Entry: close crosses below lower_band on bar t (band touch) AND range
  regime holds AND close[t] > close[t-1] is checked on t+1 (the
  stall/reversal confirmation bar) -- i.e. entry fires on the first bar
  after a lower-band touch where price ticks up.
- Exit: close >= vwap (reversion target reached), OR close <= lower_band -
  stop_buffer * vw_std (stop-out, band re-stretch), OR a max_hold_days
  time-stop, OR the range regime flips to trending (ADX >= threshold).

Interface contract matches strategies/2026-09-03_bb_meanrev_qqq_volregime.py:
generate_signals(price_df, **params) -> pd.Series {0,1}
generate_returns(price_df, **params) -> pd.Series of daily strategy returns
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _adx(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1.0 / period, adjust=False).mean() / atr.replace(0.0, float("nan")))
    minus_di = 100 * (minus_dm.ewm(alpha=1.0 / period, adjust=False).mean() / atr.replace(0.0, float("nan")))
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, float("nan"))
    adx = dx.ewm(alpha=1.0 / period, adjust=False).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    vwap_window: int = 20,
    band_mult: float = 2.0,
    stop_buffer: float = 0.5,
    adx_period: int = 14,
    adx_threshold: float = 25.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, volume = df["close"], df["volume"]

    pv = close * volume
    rolling_vol_sum = volume.rolling(vwap_window).sum()
    vwap = pv.rolling(vwap_window).sum() / rolling_vol_sum.replace(0.0, float("nan"))

    # Volume-weighted variance of close around the rolling VWAP.
    sq_dev = (close - vwap) ** 2
    vw_var = (sq_dev * volume).rolling(vwap_window).sum() / rolling_vol_sum.replace(0.0, float("nan"))
    vw_std = vw_var.clip(lower=0.0) ** 0.5

    lower_band = vwap - band_mult * vw_std
    stop_level_series = lower_band - stop_buffer * vw_std

    adx = _adx(df, adx_period)
    range_regime = adx < adx_threshold

    band_touch = close < lower_band
    stall_confirm = close > close.shift(1)
    # Entry fires the bar AFTER a band touch, with a same-bar up-tick.
    entry_signal = band_touch.shift(1).fillna(False) & stall_confirm & range_regime.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            c = close.iloc[i]
            hit_target = bool(c >= vwap.iloc[i]) if not math.isnan(vwap.iloc[i]) else False
            hit_stop = bool(c <= stop_level_series.iloc[i]) if not math.isnan(stop_level_series.iloc[i]) else False
            regime_flip = not bool(range_regime.iloc[i]) if not pd.isna(range_regime.iloc[i]) else False
            if hit_target or hit_stop or held >= max_hold_days or regime_flip:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
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
