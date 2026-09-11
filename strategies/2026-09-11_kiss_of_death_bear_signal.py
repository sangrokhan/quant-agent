"""Strategy: The Kiss of Death (monthly-bar bear-market anticipation signal).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-075):
Per QuantifiedStrategies.com's disclosed rule
(https://www.quantifiedstrategies.com/kiss-of-death-trading-strategy/,
visited this iteration -- full rule + backtest disclosed), the "Kiss of
Death" is a rare monthly-bar sell signal that has historically preceded
major bear markets (1969, 1973, 1978, 2001, 2008, and a false positive
in 2022): the index (1) makes an all-time high, (2) subsequently closes a
month BELOW its 21-month EMA, (3) bounces back and closes a month ABOVE
the 21-month EMA, (4) then closes a month BELOW the low it made just
before that bounce (step 3). On step 4's confirmation, exit/flip flat;
re-enter (go long again) when the index closes a month above its 10-month
EMA. Source's own SPX backtest since 1967: CAGR 9.08% (vs buy-and-hold
7.11%), time in market 87.9%, max drawdown 30.17% (vs buy-and-hold
52.56%).

This is the first monthly-bar, multi-step ("all-time-high -> EMA
break -> failed bounce -> lower-low confirmation") sequential pattern
signal in this repo -- distinct from every prior single-condition
trend/momentum/oscillator signal, and from the already-tested single-line
21-EMA slope/crossover strategies (this uses the 21-EMA as a
tripwire within a specific 4-step sequence, not as a standalone
trend filter).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} long/flat)

Note: price_df is expected as DAILY OHLCV (per data/loaders.py); this
module resamples internally to monthly bars to run the signal logic
(matching the source's own monthly-bar construction), then forward-fills
the resulting monthly position back onto the daily index (no look-ahead:
a month's close-derived signal only takes effect for the FOLLOWING
month's daily bars).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _monthly_close(df: pd.DataFrame) -> pd.Series:
    idx = pd.to_datetime(df.index).tz_localize(None)
    close = df["close"].copy()
    close.index = idx
    return close.resample("ME").last().dropna()


def _monthly_signal(monthly_close: pd.Series, ema_fast: int = 21, ema_slow: int = 10) -> pd.Series:
    """Return a {0,1} monthly long/flat position, indexed at each month-end,
    representing the position to hold for the FOLLOWING month."""
    ema21 = monthly_close.ewm(span=ema_fast, adjust=False).mean()
    ema10 = monthly_close.ewm(span=ema_slow, adjust=False).mean()
    running_ath = monthly_close.cummax()

    n = len(monthly_close)
    state = "long"  # long | waiting_for_bounce | bounced_watch_lowerlow
    pre_bounce_low = None
    position = pd.Series(1, index=monthly_close.index, dtype=int)

    for i in range(n):
        c = monthly_close.iloc[i]
        e21 = ema21.iloc[i]
        e10 = ema10.iloc[i]
        ath_so_far = running_ath.iloc[i]

        if state == "long":
            # look for a close below 21-EMA after having made an ATH
            if c == ath_so_far:
                pass  # fresh ATH, stay long
            if c < e21:
                state = "below_ema_watch_bounce"
                pre_bounce_low = c
            position.iloc[i] = 1

        elif state == "below_ema_watch_bounce":
            if c < pre_bounce_low:
                pre_bounce_low = c
            if c > e21:
                state = "bounced_watch_lowerlow"
            position.iloc[i] = 1

        elif state == "bounced_watch_lowerlow":
            if c < pre_bounce_low:
                # KISS OF DEATH confirmed -- exit to flat
                state = "flat_waiting_reentry"
                position.iloc[i] = 0
            elif c < e21:
                # dropped back below 21-EMA without confirming lower low yet;
                # reset the pre-bounce low tracking to this new dip
                state = "below_ema_watch_bounce"
                pre_bounce_low = c
                position.iloc[i] = 1
            else:
                position.iloc[i] = 1

        elif state == "flat_waiting_reentry":
            if c > e10:
                state = "long"
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_signals(
    price_df: pd.DataFrame,
    ema_fast: int = 21,
    ema_slow: int = 10,
) -> pd.Series:
    """Return a daily {0,1} long/flat position series (forward-filled from
    the monthly signal, applied to the NEXT month's daily bars -- no
    look-ahead)."""
    df = _prep(price_df)
    monthly_close = _monthly_close(df)
    monthly_pos = _monthly_signal(monthly_close, ema_fast=ema_fast, ema_slow=ema_slow)

    daily_index = pd.to_datetime(df.index).tz_localize(None)
    # Shift the monthly position forward by one month-end so a given
    # month's close-derived decision applies to the FOLLOWING month's bars.
    monthly_pos_shifted = monthly_pos.shift(1).fillna(1).astype(int)
    monthly_pos_shifted.index = monthly_pos_shifted.index + pd.offsets.MonthEnd(0)

    daily_pos = monthly_pos_shifted.reindex(daily_index, method="ffill")
    daily_pos = daily_pos.fillna(1).astype(int)
    daily_pos.index = df.index
    return daily_pos


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
