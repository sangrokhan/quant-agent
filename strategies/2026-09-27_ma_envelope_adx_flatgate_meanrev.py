"""Strategy: Moving Average Envelope mean reversion, gated to ONLY fire when
ADX signals a flat/non-trending regime.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-106),
sourced from:
  - StockCharts ChartSchool "Moving Average Envelopes"
    (https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-average-envelopes,
    visited this iteration): "With a moving average as the base, Moving
    Average Envelopes can be used as a trend following indicator. Beyond
    simply trend following, though, the envelopes can also be used to
    identify overbought and oversold levels when the trend is relatively
    flat... Sometimes a strong trend does not take hold after an envelope
    break and prices move into a trading range. Such trading ranges are
    marked by a relatively flat moving average. The envelopes can then be
    used to identify overbought and oversold levels for trading purposes."

This repo has tested unconditional MA-Envelope mean reversion multiple times
(2026-09-04-065 rejected, 2026-09-06-106 rejected) and MA-Envelope trend
breakout (2026-09-06-096 rejected). Both prior variants traded the envelope
touch/break UNCONDITIONALLY regardless of whether the underlying trend was
flat or strong -- which the source explicitly warns against ("moves above or
below the envelopes warrant attention [as trend starts]... Sometimes a
strong trend does not take hold... trading ranges are marked by a relatively
flat moving average"). This iteration operationalizes that missing regime
condition directly: only take the mean-reversion trade when ADX(adx_window)
is BELOW adx_flat_threshold (confirming "relatively flat" trend per the
source's own qualifier), suppressing the mean-reversion trades during
strongly trending regimes where an envelope touch is more likely to
foreshadow a breakout/continuation rather than a reversion.

Signal logic
------------
- MA[t]  = SMA(close, ma_window)[t].
- Lower band[t] = MA[t] * (1 - envelope_pct); Upper band[t] = MA[t] * (1 + envelope_pct).
- ADX(adx_window) computed via standard Wilder's DM/TR smoothing.
- Long entry: close crosses back ABOVE the lower band after closing at/below
  it the prior bar (touch-then-reclaim, same operationalization as
  2026-09-06-106) AND ADX[t] < adx_flat_threshold (flat-trend gate, the new
  element this iteration).
- Exit: close reaches/crosses back above the central MA line (source's
  stated mean-reversion take-profit target), OR ADX rises back above
  adx_flat_threshold (regime flip -- trend is no longer flat, source's own
  rationale for exiting the mean-reversion premise), OR a max_hold_days
  time-stop (repo standard safety valve).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
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


def _envelope(df: pd.DataFrame, ma_window: int, envelope_pct: float):
    ma = df["close"].rolling(ma_window, min_periods=ma_window).mean()
    lower = ma * (1.0 - envelope_pct)
    upper = ma * (1.0 + envelope_pct)
    return ma, lower, upper


def _adx(df: pd.DataFrame, adx_window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_dm = pd.Series(plus_dm, index=df.index)
    minus_dm = pd.Series(minus_dm, index=df.index)

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / adx_window, adjust=False, min_periods=adx_window).mean()
    plus_di = 100.0 * (plus_dm.ewm(alpha=1.0 / adx_window, adjust=False, min_periods=adx_window).mean() / atr.replace(0, np.nan))
    minus_di = 100.0 * (minus_dm.ewm(alpha=1.0 / adx_window, adjust=False, min_periods=adx_window).mean() / atr.replace(0, np.nan))

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1.0 / adx_window, adjust=False, min_periods=adx_window).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    ma_window: int = 20,
    envelope_pct: float = 0.05,
    adx_window: int = 14,
    adx_flat_threshold: float = 20.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ma, lower, upper = _envelope(df, ma_window, envelope_pct)
    adx = _adx(df, adx_window)
    flat_regime = adx < adx_flat_threshold

    was_below_or_at = close.shift(1) <= lower.shift(1)
    crossed_back_up = (close > lower) & was_below_or_at.fillna(False)
    entry_signal = crossed_back_up & flat_regime.fillna(False)

    reached_ma = close >= ma
    regime_flip = ~flat_regime.fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_days = 0

    entry_arr = entry_signal.to_numpy()
    reached_ma_arr = reached_ma.to_numpy()
    regime_flip_arr = regime_flip.to_numpy()
    pos_arr = np.zeros(len(df), dtype=int)

    for i in range(len(df)):
        if in_position:
            hold_days += 1
            if reached_ma_arr[i] or regime_flip_arr[i] or hold_days >= max_hold_days:
                in_position = False
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_position = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    position = pd.Series(pos_arr, index=df.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    ma_window: int = 20,
    envelope_pct: float = 0.05,
    adx_window: int = 14,
    adx_flat_threshold: float = 20.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (position lagged 1 day)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        ma_window=ma_window,
        envelope_pct=envelope_pct,
        adx_window=adx_window,
        adx_flat_threshold=adx_flat_threshold,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
