"""Strategy: OBV bullish divergence + swing-high breakout confirmation,
gated by a trend/RSI-recovery filter (distinct confirmation mechanic from
prior OBV-divergence attempts in this repo).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-119):
Per a Google AI-overview synthesis (TradersPost/Phemex/equiti.com sourced)
of OBV bullish-divergence strategy rules: price records a lower low while
OBV (cumulative volume, +vol on up-close days, -vol on down-close days)
records a higher low over the same lookback -- "hidden accumulation" before
a potential reversal. Entry trigger: wait for price to close above the
recent intermediate swing high between the two lows (confirmation that
buyers have taken control, not entering on the raw divergence signal
alone). Optional filter (this implementation includes both): price above a
50-period SMA trend baseline, and RSI moving back above 30 (avoid catching
a falling knife). Exit: close breaking back below the divergence low (stop)
or a max_hold_days time-stop.

Distinct from existing OBV-family entries in this repo:
- 2026-09-04-027 (accepted QQQ only): OBV-vs-its-own-EMA crossover, no
  divergence detection at all -- pure momentum confirmation filter.
- 2026-09-04-088 (rejected): divergence detection but confirms entry via a
  short EMA cross-back, stop below the divergence low, NO trend/RSI filter.
This strategy differs from 088 via (a) the swing-high breakout confirmation
mechanic (source's specific "close above the intermediate swing high, not
an EMA cross") and (b) adding the source's own suggested 50-SMA trend
filter + RSI>30 recovery filter combo, directly targeting 088's likely
failure mode (whipsaw entries with no trend/momentum context).

Signal logic
------------
- OBV = cumulative sum of signed daily volume (+volume on up-close days,
  -volume on down-close days, 0 on flat).
- Over a `lookback` window, detect: price makes a new `lookback`-bar low
  (close[t] == rolling_min(close, lookback)) while OBV does NOT make a
  new `lookback`-bar low at the same bar (OBV[t] > rolling_min(OBV,
  lookback) computed over the prior `lookback` bars, i.e. divergence).
- Once divergence flagged at bar t, track the "divergence swing high" =
  max(high) over the `confirm_window` bars following t (rolling forward
  window capturing the local swing high between the divergence low and
  now).
- Entry (long): close breaks above that tracked swing high, AND
  close > SMA(trend_window), AND RSI(rsi_window) has just crossed back
  above rsi_recovery_level (from below) within the same confirm_window.
- Exit: close < the divergence-low price (stop) OR max_hold_days time-stop.
- Flat otherwise; long-only, no shorting.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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


def _obv(df: pd.DataFrame) -> pd.Series:
    close = df["close"]
    vol = df["volume"]
    direction = np.sign(close.diff()).fillna(0.0)
    return (direction * vol).cumsum()


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 20,
    confirm_window: int = 10,
    trend_window: int = 50,
    rsi_window: int = 14,
    rsi_recovery_level: float = 30.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    n = len(close)

    obv = _obv(df)
    rolling_low_close = close.rolling(lookback).min()
    rolling_low_obv = obv.rolling(lookback).min()
    price_new_low = (close == rolling_low_close).fillna(False)
    # OBV divergence: at the same bar price makes a new low, OBV is
    # strictly above its own trailing rolling low (i.e. not confirming).
    obv_diverging = (obv > rolling_low_obv).fillna(False)
    divergence_flag = (price_new_low & obv_diverging).fillna(False)

    trend_sma = close.rolling(trend_window).mean()
    uptrend = (close > trend_sma).fillna(False)
    rsi = _rsi(close, rsi_window)
    rsi_ok = (rsi > rsi_recovery_level).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_day = -1
    stop_level = np.nan
    # Track pending divergence: (div_bar_index, div_low_price, swing_high_so_far)
    pending = None

    close_arr = close.values
    high_arr = high.values
    div_arr = divergence_flag.values
    uptrend_arr = uptrend.values
    rsi_recover_arr = rsi_ok.values

    for i in range(n):
        if in_position:
            if close_arr[i] < stop_level or (i - entry_day) >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                pending = None
                continue
            position.iloc[i] = 1
            continue

        # Update / expire pending divergence tracker
        if pending is not None:
            div_bar, div_low, swing_high = pending
            if (i - div_bar) > confirm_window:
                pending = None
            else:
                # Breakout check uses the swing high accumulated STRICTLY
                # before today's bar (today's own high shouldn't count
                # against today's own close for the breakout trigger).
                if (
                    close_arr[i] > swing_high
                    and uptrend_arr[i]
                    and any(rsi_recover_arr[max(div_bar, i - confirm_window):i + 1])
                ):
                    in_position = True
                    entry_day = i
                    stop_level = div_low
                    position.iloc[i] = 1
                    pending = None
                    continue
                # No breakout yet -- extend the tracked swing high with
                # today's bar for future comparisons.
                pending = (div_bar, div_low, max(swing_high, high_arr[i]))

        if div_arr[i]:
            pending = (i, close_arr[i], high_arr[i])

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
