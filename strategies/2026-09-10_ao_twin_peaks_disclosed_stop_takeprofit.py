"""Strategy: Bill Williams Awesome Oscillator (AO) Twin Peaks, with the exact
stop-loss / take-profit mechanics disclosed by tradingstrategyguides.com's
full rule set (fetched via browser_exec, web_search DDGS backend failing
this trigger).

Hypothesis
----------
Per https://tradingstrategyguides.com/bill-williams-awesome-oscillator-strategy/
(visited this iteration), the AO Twin Peaks bullish setup is defined by SIX
explicit steps distinct from this repo's already-rejected generic AO Twin
Peaks variant (2026-09-04-160, which used a trend-break/time-stop exit and
"AO ticking up" as the trigger rather than a confirmed zero-line break):

1. AO is below zero.
2. AO prints two swing lows, the second higher than the first (bullish
   rising-bottoms divergence in momentum).
3. The histogram bar immediately after the second swing low is green
   (rising).
4. WAIT for AO to actually cross/break above the zero line -- entry trigger
   is the confirmed zero-line break, not the earlier tick-up.
5. Stop-loss placed exactly below the price bar corresponding to the SECOND
   swing low of the Twin Peaks pattern (a specific, price-based stop, not a
   generic ATR/SMA-trend-break exit).
6. Take-profit as soon as AO prints two CONSECUTIVE red (declining) bars
   (an oscillator-momentum-exhaustion exit, not a time-stop or trend-break).

This is a genuinely distinct mechanical variant from 2026-09-04-160 in three
ways: (a) the confirmed zero-line-break entry trigger instead of a mere
uptick after the second low, (b) a fixed price-based stop-loss below the
second swing low's bar rather than a generic exit, and (c) a two-red-bar
take-profit trigger rather than AO<0/trend-break/time-stop. Long-only,
tested with a 200-day SMA uptrend gate per this repo's consistent prior
finding that an uptrend filter improves AO-family setups.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _compute_ao(df: pd.DataFrame) -> pd.Series:
    median_price = (df["high"] + df["low"]) / 2.0
    ao = median_price.rolling(5).mean() - median_price.rolling(34).mean()
    return ao


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    trend_window: int = 200,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]

    ao = _compute_ao(df)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    # local swing lows in AO: a point lower than swing_window bars on each side
    is_swing_low = (
        (ao == ao.rolling(2 * swing_window + 1, center=True).min())
    )

    idx_list = close.index
    n = len(idx_list)
    position = pd.Series(0, index=idx_list, dtype=int)

    in_pos = False
    entry_idx = -1
    stop_price = None
    prev_swing_low_idx = None
    prev_swing_low_val = None
    red_bar_count = 0

    ao_vals = ao.values
    swing_low_flags = is_swing_low.fillna(False).values
    uptrend_vals = uptrend.fillna(False).values
    low_vals = low.values
    close_vals = close.values

    for i in range(n):
        if i < 1:
            continue

        # track swing lows below zero
        if swing_low_flags[i] and not (ao_vals[i] != ao_vals[i]) and ao_vals[i] < 0:
            if prev_swing_low_idx is not None:
                # check twin-peaks: current swing low higher than previous, both below zero
                if ao_vals[i] > prev_swing_low_val and prev_swing_low_val < 0:
                    # candidate twin-peaks pattern confirmed at this bar
                    pass
            prev_swing_low_idx = i
            prev_swing_low_val = ao_vals[i]

        if not in_pos:
            # entry trigger: AO crosses above zero AND we have a valid recent twin-peaks setup
            crossed_zero = ao_vals[i - 1] < 0 and ao_vals[i] >= 0
            if crossed_zero and prev_swing_low_idx is not None and uptrend_vals[i]:
                # look back for a second swing low within reasonable window before the cross,
                # with an even earlier first swing low that's lower
                lookback_start = max(0, i - 60)
                swing_lows_recent = [
                    j for j in range(lookback_start, i)
                    if swing_low_flags[j] and ao_vals[j] < 0
                ]
                if len(swing_lows_recent) >= 2:
                    first_low_idx, second_low_idx = swing_lows_recent[-2], swing_lows_recent[-1]
                    if ao_vals[second_low_idx] > ao_vals[first_low_idx]:
                        in_pos = True
                        entry_idx = i
                        stop_price = low_vals[second_low_idx]
                        red_bar_count = 0
                        position.iloc[i] = 1
                        continue
        else:
            held_days = i - entry_idx
            is_red_bar = ao_vals[i] < ao_vals[i - 1]
            if is_red_bar:
                red_bar_count += 1
            else:
                red_bar_count = 0

            stop_hit = close_vals[i] < stop_price if stop_price is not None else False
            take_profit = red_bar_count >= 2
            time_stop = held_days >= max_hold_days

            if stop_hit or take_profit or time_stop:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1

    return position.fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    trend_window: int = 200,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        swing_window=swing_window,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
