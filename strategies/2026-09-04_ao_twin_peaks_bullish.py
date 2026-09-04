"""Strategy: Awesome Oscillator "Bullish Twin Peaks" divergence-bottom
setup, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-160):
Bill Williams' Awesome Oscillator (AO = SMA(5, median_price) -
SMA(34, median_price), median_price = (high+low)/2) has a "Twin Peaks"
setup, per TradingSim's Awesome Oscillator guide (rated their favorite of
AO's 3 common strategies since it accounts for the current setup context,
unlike the raw zero-line cross already tested in this repo at
2026-09-04-041, near-miss Sharpe 0.89): a Bullish Twin Peaks forms when
(1) AO is below the zero line, (2) there are two swing lows in AO with
the second HIGHER than the first (a rising-bottoms bullish divergence
below zero -- selling momentum is fading even though price may still be
weak), and (3) the histogram bar immediately after the second (higher)
low is green (AO ticking up). This is distinct from both the raw
zero-line-cross AO strategy (2026-09-04-041) and the Bullish Saucer AO
strategy (2026-09-04-111) already tested in this repo -- Twin Peaks is
specifically a divergence/higher-low pattern below zero, not a
zero-line-cross or a 3-bar saucer shape.

Signal logic
------------
- AO = rolling(5).mean(median_price) - rolling(34).mean(median_price).
- Detect local swing lows in AO via a simple `swing_window`-bar pivot
  test (AO[i] is the minimum within +/- swing_window bars).
- A Bullish Twin Peaks fires when: the two most recent confirmed AO swing
  lows are both below zero, the second (more recent) low is higher than
  the first, AND the bar right after the second low has AO rising
  (green histogram bar, i.e. AO[t] > AO[t-1]).
- Long entry: on the Twin-Peaks-confirmation bar, gated by close >
  SMA(trend_window) (per the source's own recommendation used throughout
  this repo's other AO strategies -- keep the same trend-following
  precondition for a fair comparison against 2026-09-04-041/111).
- Exit: AO crosses back below zero (per the source's stated bearish
  reversal signal for this contrarian-below-zero setup), the trend
  filter breaks, or a max_hold_days time-stop.
- Flat (no position) whenever not in an active long.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1} position series
    generate_returns(price_df, **params) -> pd.Series daily strategy returns
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _awesome_oscillator(df: pd.DataFrame) -> pd.Series:
    median_price = (df["high"] + df["low"]) / 2.0
    ao = median_price.rolling(5).mean() - median_price.rolling(34).mean()
    return ao


def _swing_lows(ao: pd.Series, swing_window: int) -> pd.Series:
    """Boolean series: True where ao[i] is the local minimum within
    +/- swing_window bars (a confirmed swing low, confirmed swing_window
    bars later since we need future bars to know it was the minimum)."""
    roll_min = ao.rolling(2 * swing_window + 1, center=True).min()
    is_low = ao == roll_min
    # Only "confirmed" swing_window bars after the pivot bar itself.
    confirmed = is_low.shift(swing_window).fillna(False).astype(bool)
    return confirmed


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 3,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ao = _awesome_oscillator(df)
    swing_low_confirmed = _swing_lows(ao, swing_window)
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    n = len(close)
    twin_peaks_entry = pd.Series(False, index=close.index)

    # Track the two most-recent confirmed swing lows (index positions, AO values).
    swing_low_positions = [i for i in range(n) if bool(swing_low_confirmed.iloc[i])]
    ao_values = ao.values

    for k in range(1, len(swing_low_positions)):
        prev_i = swing_low_positions[k - 1]
        curr_i = swing_low_positions[k]
        prev_val = ao_values[prev_i]
        curr_val = ao_values[curr_i]
        if pd.isna(prev_val) or pd.isna(curr_val):
            continue
        if prev_val < 0 and curr_val < 0 and curr_val > prev_val:
            # Bullish divergence detected at curr_i; look for the first
            # green (AO rising) bar strictly after curr_i to confirm.
            confirm_i = None
            for j in range(curr_i + 1, min(curr_i + 6, n)):
                if pd.isna(ao_values[j]) or pd.isna(ao_values[j - 1]):
                    continue
                if ao_values[j] > ao_values[j - 1]:
                    confirm_i = j
                    break
            if confirm_i is not None:
                twin_peaks_entry.iloc[confirm_i] = True

    entry = twin_peaks_entry & uptrend.fillna(False)
    exit_zero_cross = ao < 0
    exit_regime_flip = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_zero_cross.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
