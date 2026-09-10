"""Strategy: Rolling VWAP + 1st-deviation-band mean reversion ("Rotation Setup").

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per https://www.trader-dale.com/simple-vwap-trading-strategies-your-guide-to-smarter-trades/
(Trader Dale's VWAP + standard-deviation-bands guide): VWAP acts as the
market's "fair value" line, with a first standard-deviation band above and
below built from the volume-weighted variance around VWAP. The source's own
"Rotation Setup" (for ranging/sideways conditions, identified when the bands
are moving roughly horizontally rather than sloping): go long when price
touches the lower first-deviation band (support), take profit at the
central VWAP line ("VWAP acts like a magnet -- price is drawn back to it
repeatedly"), stop-loss just beyond the band. This implementation adapts the
source's intraday-session VWAP concept to a rolling N-day VWAP (this repo
only has daily OHLCV bars, no intraday session boundaries), and operationalizes
"bands moving horizontally" (source's qualitative ranging-regime filter) as a
realized-volatility-based regime gate: only take Rotation-Setup entries when
the rolling VWAP band width itself is NOT expanding (band_width <= its own
trailing median), approximating the source's "the bands aren't sloping / the
market is calm" condition without visual band-slope inspection. First
rolling-VWAP-with-stdev-bands mean-reversion strategy in this repo --
distinct from Anchored VWAP crossover/reclaim variants already tested (which
use no deviation bands).

Signal logic
------------
- Rolling VWAP[t] = sum(typical_price * volume, vwap_window) / sum(volume, vwap_window)
  where typical_price = (high+low+close)/3.
- Rolling VW variance = sum(volume * (typical_price - VWAP)^2, vwap_window) / sum(volume, vwap_window)
  -> Rolling VW stdev = sqrt(that variance); lower band = VWAP - dev_mult * stdev.
- Regime gate: band_width = (upper - lower); ranging regime when
  band_width <= its own trailing (band_width_lookback) median (source's
  "horizontal bands" condition, approximated numerically).
- Entry (long): close crosses below (touches/pierces) the lower band while
  in the ranging regime.
- Exit: close crosses back above the rolling VWAP (source's own take-profit
  target), OR a max_hold_days time-stop backstop (added safety net, since
  the source's own stop-loss-on-band-break isn't directly reproducible
  without intraday data).

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


def generate_signals(
    price_df: pd.DataFrame,
    vwap_window: int = 20,
    dev_mult: float = 1.0,
    band_width_lookback: int = 100,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"].astype(float).replace(0, np.nan)

    typical_price = (high + low + close) / 3.0

    pv = typical_price * volume
    rolling_pv_sum = pv.rolling(vwap_window).sum()
    rolling_vol_sum = volume.rolling(vwap_window).sum()
    vwap = rolling_pv_sum / rolling_vol_sum

    sq_dev = volume * (typical_price - vwap) ** 2
    rolling_sq_dev_sum = sq_dev.rolling(vwap_window).sum()
    vw_variance = rolling_sq_dev_sum / rolling_vol_sum
    vw_stdev = np.sqrt(vw_variance.clip(lower=0))

    lower_band = vwap - dev_mult * vw_stdev
    upper_band = vwap + dev_mult * vw_stdev
    band_width = upper_band - lower_band
    band_width_median = band_width.rolling(band_width_lookback).median()
    ranging_regime = band_width <= band_width_median

    below_lower = close < lower_band
    above_vwap = close > vwap

    entry_signal = (below_lower & ranging_regime).fillna(False)
    exit_signal = above_vwap.fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_days = 0
    entry_vals = entry_signal.values
    exit_vals = exit_signal.values

    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            exit_now = exit_vals[i] or (hold_days >= max_hold_days)
            if exit_now:
                in_pos = False
                hold_days = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_vals[i]:
                in_pos = True
                hold_days = 0
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    vwap_window: int = 20,
    dev_mult: float = 1.0,
    band_width_lookback: int = 100,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        vwap_window=vwap_window,
        dev_mult=dev_mult,
        band_width_lookback=band_width_lookback,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0)
    return strat_ret
