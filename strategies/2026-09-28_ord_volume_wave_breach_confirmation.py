"""Strategy: Ord Volume wave-average breach confirmation, long-only trend entry.

Hypothesis (source: https://www.tradingview.com/script/lhda3xOg-Ord-Volume-LucF/,
read 2026-09-28 via browser_exec -- TradingView's "Ord Volume [LucF]"
open-source indicator page, itself documenting Tim Ord's "Ord Volume"
concept from his 2004 Stocks & Commodities articles / "The Secret Science
of Price and Volume" book):

Ord Volume divides price action into alternating up/down "waves" (defined
by a trend break: a new wave starts whenever price crosses a short trend
filter in the opposite direction) and tracks each wave's AVERAGE volume
(not cumulative, unlike Weis Wave). The source's own "Marker 1" concept:
"triggers when the current wave's average volume breaches the previous
wave's highest average volume" -- i.e. the market is putting in MORE
average participation on this up-move than the prior up-move managed,
which Ord treats as confirmation of renewed/strengthening buying pressure
(a volume-based trend-confirmation signal, distinct from pure price
breakouts). This repo has 0 prior hits for "Ord Volume" or "Weis Wave" in
strategies_index.jsonl -- genuinely new indicator family, distinct from
already-tested Klinger/Chaikin/OBV-style cumulative volume indicators
(Ord's average-based wave measure is a different construction).

Operationalized here as a long-only daily-bar strategy: define a wave as a
contiguous run of price closes above (up-wave) or below (down-wave) an
EMA(trend_window) trend filter. Track running average daily volume within
the CURRENT up-wave. Enter/stay long once the current up-wave's running
average volume exceeds the PRIOR completed up-wave's average volume
(the "breach" -- Marker 1's own confirmation condition), for as long as
the trend filter holds. Exit on trend-filter break (wave ends) or a
max_hold_days time-stop, whichever comes first.

Signal logic:
- wave state: up_wave = close > EMA(trend_window); a new wave starts when
  up_wave flips value vs the prior bar.
- running average volume of the CURRENT up-wave = cumulative mean of
  volume since this up-wave started.
- prior up-wave's average volume = the running average volume at the
  moment the previous up-wave ended (its final running mean).
- entry/hold condition: currently in an up-wave AND current up-wave's
  running average volume > prior completed up-wave's average volume
  (volume_breach_mult can scale this threshold, default 1.0 = exact
  Marker 1 condition).
- exit: up-wave ends (close crosses back below EMA) OR max_hold_days
  reached, whichever first.
- first up-wave in the series (no prior up-wave average yet) never
  triggers (need at least one completed up-wave as a benchmark).

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 20,
    volume_breach_mult: float = 1.0,
    min_wave_len: int = 3,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"].astype(float)

    ema = close.ewm(span=trend_window, adjust=False).mean()
    up_wave = (close > ema).to_numpy()
    vol_arr = volume.to_numpy()
    n = len(df)

    pos = pd.Series(0.0, index=df.index)

    prior_up_wave_avg = None  # average volume of the last COMPLETED up-wave
    cur_wave_is_up = None
    cur_wave_start = 0
    cur_wave_vol_sum = 0.0
    cur_wave_len = 0

    in_pos = False
    hold_count = 0

    for i in range(n):
        wave_now_up = bool(up_wave[i])

        if cur_wave_is_up is None:
            cur_wave_is_up = wave_now_up
            cur_wave_start = i
            cur_wave_vol_sum = 0.0
            cur_wave_len = 0

        if wave_now_up != cur_wave_is_up:
            # current wave just ended -- if it was an up-wave, record its
            # average volume as the new benchmark for future up-waves.
            if cur_wave_is_up and cur_wave_len > 0:
                prior_up_wave_avg = cur_wave_vol_sum / cur_wave_len
            cur_wave_is_up = wave_now_up
            cur_wave_start = i
            cur_wave_vol_sum = 0.0
            cur_wave_len = 0

        cur_wave_vol_sum += vol_arr[i]
        cur_wave_len += 1
        cur_wave_avg = cur_wave_vol_sum / cur_wave_len if cur_wave_len > 0 else 0.0

        breach = (
            wave_now_up
            and cur_wave_len >= min_wave_len
            and prior_up_wave_avg is not None
            and cur_wave_avg > volume_breach_mult * prior_up_wave_avg
        )

        if in_pos:
            hold_count += 1
            exit_now = (not wave_now_up) or hold_count >= max_hold_days
            if exit_now:
                in_pos = False
                hold_count = 0
            else:
                pos.iloc[i] = 1.0

        if not in_pos and breach:
            in_pos = True
            hold_count = 0
            pos.iloc[i] = 1.0

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 20,
    volume_breach_mult: float = 1.0,
    min_wave_len: int = 3,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        trend_window=trend_window,
        volume_breach_mult=volume_breach_mult,
        min_wave_len=min_wave_len,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret
