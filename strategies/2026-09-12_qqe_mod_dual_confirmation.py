"""Strategy: QQE MOD (dual-QQE with Bollinger Band zero-line confirmation).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per https://www.tradingview.com/script/TpUW4muw-QQE-MOD/ (Mihkel00, creator's
own page) and https://ataquant.com/trading-strategy-with-qqe-mod-indicator/
(worked entry-rule example): "QQE MOD" combines TWO separate QQE (Qualitative
Quantitative Estimation) calculations -- a "fast" one whose trend state is
shown as a histogram, and a "slow" one that is zero-centered and passed
through Bollinger Bands acting as a confirmation "zero line" -- and only
signals when both agree ("When both of them agree - you get a blue or a red
bar"). This is a DIFFERENT construction from the already-tested single-QQE
strategy in this repo (2026-09-08-162, rejected: plain smoothed-RSI-vs-ATR
trailing-band crossover with an EMA(100) trend gate, failed parameter
sensitivity + SPY/crypto). Here there is no separate SMA/EMA trend filter;
the SECOND QQE (with its own Bollinger-Band zero-line) is itself the
confirmation/trend-filter mechanism, which is the entire point of the "MOD"
variant per the source.

QQE construction (standard, per multiple public Pine ports of Glaz's
original QQE + Mihkel00's MOD):
    RSI(rsi_period) -> RsiMa = EMA(RSI, smooth)
    AtrRsi = |RsiMa[t-1] - RsiMa[t]|
    MaAtrRsi = EMA(AtrRsi, wilders_period)      # wilders_period = rsi_period*2-1
    DeltaFastAtrRsi = EMA(MaAtrRsi, wilders_period) * qqe_factor
    newshortband = RsiMa + DeltaFastAtrRsi; newlongband = RsiMa - DeltaFastAtrRsi
    longband/shortband are ratcheted trailing bands (SuperTrend-style state
    machine); trend flips to +1 when RsiMa crosses above the (previous)
    shortband, flips to -1 when RsiMa crosses below the (previous) longband.

Signal logic
------------
- FAST QQE: rsi_period=6, smooth=5, qqe_factor=1.61 (source's own histogram
  defaults) -> fast_trend in {+1,-1}.
- SLOW QQE: rsi_period=6, smooth=5, qqe_factor=2.428 (source's own
  "background" QQE defaults) -> RsiMa_slow, zero-centered as
  slow_zero = RsiMa_slow - 50.
- Bollinger Bands (bb_length=50, bb_mult=0.35, source's own disclosed
  defaults) computed ON slow_zero act as the confirmation "zero line".
- Long entry: fast_trend flips to +1 (bullish) AND slow_zero > upper BB
  (both QQEs agreeing bullish, per source's "blue bar" rule).
- Exit: fast_trend flips to -1, OR slow_zero drops back below the BB
  midline (0, confirmation lost), OR a max_hold_days time-stop.

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


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def _qqe(close: pd.Series, rsi_period: int, smooth: int, qqe_factor: float) -> tuple[pd.Series, pd.Series]:
    """Returns (RsiMa, trend) where trend is a {+1,-1} state series."""
    wilders_period = max(rsi_period * 2 - 1, 2)

    rsi = _rsi(close, rsi_period)
    rsi_ma = rsi.ewm(span=smooth, min_periods=smooth, adjust=False).mean()

    atr_rsi = rsi_ma.diff().abs()
    ma_atr_rsi = atr_rsi.ewm(span=wilders_period, min_periods=wilders_period, adjust=False).mean()
    delta_fast_atr_rsi = ma_atr_rsi.ewm(span=wilders_period, min_periods=wilders_period, adjust=False).mean() * qqe_factor

    rsi_ma_v = rsi_ma.to_numpy()
    delta_v = delta_fast_atr_rsi.to_numpy()
    n = len(close)

    longband = np.full(n, np.nan)
    shortband = np.full(n, np.nan)
    trend = np.zeros(n, dtype=int)

    for i in range(n):
        if np.isnan(rsi_ma_v[i]) or np.isnan(delta_v[i]):
            continue
        new_long = rsi_ma_v[i] - delta_v[i]
        new_short = rsi_ma_v[i] + delta_v[i]

        prev_long = longband[i - 1] if i > 0 and not np.isnan(longband[i - 1]) else new_long
        prev_short = shortband[i - 1] if i > 0 and not np.isnan(shortband[i - 1]) else new_short
        prev_rsi_ma = rsi_ma_v[i - 1] if i > 0 else rsi_ma_v[i]

        if prev_rsi_ma > prev_long and rsi_ma_v[i] > prev_long:
            longband[i] = max(prev_long, new_long)
        else:
            longband[i] = new_long

        if prev_rsi_ma < prev_short and rsi_ma_v[i] < prev_short:
            shortband[i] = min(prev_short, new_short)
        else:
            shortband[i] = new_short

        prev_trend = trend[i - 1] if i > 0 else 0
        if rsi_ma_v[i] > prev_short:
            trend[i] = 1
        elif rsi_ma_v[i] < prev_long:
            trend[i] = -1
        else:
            trend[i] = prev_trend

    return rsi_ma, pd.Series(trend, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    fast_rsi_period: int = 6,
    fast_smooth: int = 5,
    fast_qqe_factor: float = 1.61,
    slow_rsi_period: int = 6,
    slow_smooth: int = 5,
    slow_qqe_factor: float = 2.428,
    bb_length: int = 50,
    bb_mult: float = 0.35,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    _, fast_trend = _qqe(close, fast_rsi_period, fast_smooth, fast_qqe_factor)
    slow_rsi_ma, _ = _qqe(close, slow_rsi_period, slow_smooth, slow_qqe_factor)
    slow_zero = slow_rsi_ma - 50.0

    bb_mid = slow_zero.rolling(bb_length, min_periods=bb_length).mean()
    bb_std = slow_zero.rolling(bb_length, min_periods=bb_length).std()
    upper_band = bb_mid + bb_mult * bb_std

    fast_bull_flip = (fast_trend == 1) & (fast_trend.shift(1) != 1)
    fast_bear_flip = fast_trend == -1
    slow_confirm = slow_zero > upper_band
    lost_confirm = slow_zero < bb_mid

    valid = (~fast_trend.isna()) & (~slow_zero.isna()) & (~upper_band.isna())

    n = len(close)
    pos_arr = np.zeros(n, dtype=int)
    fb_v = fast_bull_flip.to_numpy()
    fbe_v = fast_bear_flip.to_numpy()
    sc_v = slow_confirm.to_numpy()
    lc_v = lost_confirm.to_numpy()
    valid_v = valid.to_numpy()

    in_pos = False
    hold_days = 0
    for i in range(n):
        if not valid_v[i]:
            pos_arr[i] = 0
            continue
        if in_pos:
            hold_days += 1
            if fbe_v[i] or lc_v[i] or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if fb_v[i] and sc_v[i]:
                in_pos = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=close.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    fast_rsi_period: int = 6,
    fast_smooth: int = 5,
    fast_qqe_factor: float = 1.61,
    slow_rsi_period: int = 6,
    slow_smooth: int = 5,
    slow_qqe_factor: float = 2.428,
    bb_length: int = 50,
    bb_mult: float = 0.35,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        fast_rsi_period=fast_rsi_period,
        fast_smooth=fast_smooth,
        fast_qqe_factor=fast_qqe_factor,
        slow_rsi_period=slow_rsi_period,
        slow_smooth=slow_smooth,
        slow_qqe_factor=slow_qqe_factor,
        bb_length=bb_length,
        bb_mult=bb_mult,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(float) * daily_returns
    return strat_returns
