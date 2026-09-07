"""Strategy: Donchian Channel false-break-and-reject mean reversion, targeting
the channel midline, RSI-confirmed -- long-only adaptation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-017):
Per https://www.algobot.live/donchian-midline-reversion-ea-mt5/ ("Donchian
Midline Reversion" MT5 EA spec): build a Donchian Channel from the
ChannelPeriod bars *before* the signal bar (so the signal bar's own pierce
doesn't distort the band). A long setup occurs when the signal bar's LOW
pierces below the (prior-bar) lower band but the bar CLOSES back inside the
channel (a rejected/failed downside breakout -- a "false break"), confirmed
by RSI being below an oversold threshold. The reversion target is the
channel MIDLINE (average of upper/lower band), not the opposite band or a
moving average -- this is a fixed-width statistical range-reversion target,
distinct from all prior Bollinger/Keltner/z-score-band mean-reversion
strategies in this repo (which target the band's own centerline moving
average, not a fixed high/low-derived Donchian midline). A minimum
channel-width-in-ATR-units filter avoids trading in compressed/dead ranges
where reversion tends to whipsaw (source's own stated rationale). First
Donchian-*midline-reversion* strategy in this repo -- prior Donchian entries
(2026-09-03-008, 2026-09-04-054/076/125, 2026-09-06-125, 2026-09-07-014) are
all *breakout* (trend-following) or breakout-fade (Turtle Soup) variants that
target a trailing stop/opposite-extreme exit, never a fixed midline target.

Signal logic (long-only; short side dropped per SAFETY.md)
------------------------------------------------------------
- Donchian upper/lower/mid computed over `channel_period` bars, shifted by 1
  bar (so the signal bar itself doesn't distort the band -- source's own
  spec).
- ATR(atr_period) via Wilder RMA for the width filter and stop buffer.
- Width filter: (upper - lower) >= min_width_atr * ATR, else skip the bar.
- RSI(rsi_period) (Wilder-style) for the oversold confirmation.
- Long entry (while flat): low < lower_band (prior-bar band) AND
  close > lower_band (closed back inside -- the rejection) AND
  RSI < rsi_oversold AND width filter passes.
- Stop-loss: entry-day low - sl_atr_mult * ATR (source's own stop-buffer
  spec, placed beyond the rejected extreme).
- Take-profit / exit target: close >= midline (reversion achieved).
- Exit: close crosses back to/above the midline target, OR close breaches
  the stop-loss, OR a max_hold_days time-stop (added since the source's own
  EA has no explicit time-stop and this repo's convention requires bounding
  worst-case holding period).

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


def _wilder_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _wilder_rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    channel_period: int = 20,
    rsi_period: int = 14,
    rsi_oversold: float = 30.0,
    atr_period: int = 14,
    min_width_atr: float = 2.0,
    sl_atr_mult: float = 1.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    upper = high.rolling(channel_period, min_periods=channel_period).max().shift(1)
    lower = low.rolling(channel_period, min_periods=channel_period).min().shift(1)
    midline = (upper + lower) / 2.0

    atr = _wilder_atr(high, low, close, atr_period)
    rsi = _wilder_rsi(close, rsi_period)

    width_ok = (upper - lower) >= (min_width_atr * atr)
    false_break = (low < lower) & (close > lower)
    entry_trigger = false_break & (rsi < rsi_oversold) & width_ok

    close_arr = close.to_numpy(dtype=float)
    low_arr = low.to_numpy(dtype=float)
    atr_arr = atr.to_numpy(dtype=float)
    mid_arr = midline.to_numpy(dtype=float)
    entry_arr = entry_trigger.fillna(False).to_numpy()

    n = len(df)
    pos_arr = [0] * n

    in_pos = False
    stop_price = np.nan
    target_price = np.nan
    hold_counter = 0

    for i in range(n):
        c = close_arr[i]
        if in_pos:
            hold_counter += 1
            exit_now = (
                c >= target_price
                or c < stop_price
                or hold_counter >= max_hold_days
            )
            if exit_now:
                in_pos = False
                stop_price = np.nan
                target_price = np.nan
                hold_counter = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            a = atr_arr[i]
            if bool(entry_arr[i]) and not np.isnan(a) and not np.isnan(mid_arr[i]):
                in_pos = True
                stop_price = low_arr[i] - sl_atr_mult * a
                target_price = mid_arr[i]
                hold_counter = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    channel_period: int = 20,
    rsi_period: int = 14,
    rsi_oversold: float = 30.0,
    atr_period: int = 14,
    min_width_atr: float = 2.0,
    sl_atr_mult: float = 1.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        channel_period=channel_period,
        rsi_period=rsi_period,
        rsi_oversold=rsi_oversold,
        atr_period=atr_period,
        min_width_atr=min_width_atr,
        sl_atr_mult=sl_atr_mult,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
