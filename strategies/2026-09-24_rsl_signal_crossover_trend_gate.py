"""Strategy: Levy Relative Strength (RSL) signal-line crossover, gated by a
longer-term SMA trend filter.

Hypothesis (knowledge_base id 2026-09-23-158):
Per Robert A. Levy's 1968 "Relative Strength as a Criterion for Investment
Selection" (background/history via
https://www.vantagepointsoftware.com/blog/relative-strength-outperformance/)
and the fully-disclosed mechanical formula documented at
https://indicators.agenatrader.com/standard-indicators/relative-strength-levy-rsl :

    RSL(period) = Close / SMA(Close, period) * 10

Levy's own canonical lookback is 27 weeks (~135 trading days); the raw
value is "balanced around the 10 marker" -- RSL > 10 means price is above
its own N-period moving average (bullish), RSL < 10 means below (bearish).
This is mechanically the SAME ratio as any close-vs-SMA trend filter, so a
plain RSL-crosses-10 rule would just duplicate the repo's many already-
saturated SMA-crossover strategies. To make this a genuinely distinct,
testable construction (not a rescale of an existing saturated family), this
strategy instead treats RSL itself as an oscillator and trades a
MACD-style SIGNAL-LINE crossover on RSL: a fast SMA of RSL crossing above/
below a slower SMA of RSL, additionally gated by a longer-term trend SMA on
raw price (avoid buying RSL upticks inside a structural downtrend). This
distinguishes it from prior close-vs-SMA crossover/regime-filter strategies
in this repo (0 prior KB hits for "RSL"/"Levy Relative Strength").

Signal logic
------------
- Compute rsl = close / close.rolling(rsl_period).mean() * 10.
- rsl_fast = rsl.rolling(fast_window).mean(); rsl_slow = rsl.rolling(slow_window).mean().
- Long entry: rsl_fast crosses above rsl_slow AND close > close.rolling(trend_window).mean()
  (trend filter, avoids buying RSL upticks in a structural downtrend).
- Exit: rsl_fast crosses below rsl_slow, OR the trend filter breaks (close
  drops below trend_window SMA), OR a max_hold_days time-stop (avoid
  indefinite holds through a stagnant RSL regime).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _compute_rsl(close: pd.Series, rsl_period: int) -> pd.Series:
    sma = close.rolling(rsl_period).mean()
    return (close / sma) * 10.0


def generate_signals(
    price_df: pd.DataFrame,
    rsl_period: int = 135,
    fast_window: int = 5,
    slow_window: int = 20,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsl = _compute_rsl(close, rsl_period)
    rsl_fast = rsl.rolling(fast_window).mean()
    rsl_slow = rsl.rolling(slow_window).mean()

    trend_sma = close.rolling(trend_window).mean()
    trend_ok = close > trend_sma

    cross_up = (rsl_fast > rsl_slow) & (rsl_fast.shift(1) <= rsl_slow.shift(1))
    cross_down = (rsl_fast < rsl_slow) & (rsl_fast.shift(1) >= rsl_slow.shift(1))

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    hold_days = 0

    cross_up_arr = cross_up.fillna(False).to_numpy()
    cross_down_arr = cross_down.fillna(False).to_numpy()
    trend_ok_arr = trend_ok.fillna(False).to_numpy()

    pos_arr = [0] * n
    for i in range(n):
        if in_pos:
            hold_days += 1
            if cross_down_arr[i] or (not trend_ok_arr[i]) or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
        else:
            if cross_up_arr[i] and trend_ok_arr[i]:
                in_pos = True
                hold_days = 0
        pos_arr[i] = 1 if in_pos else 0

    position = pd.Series(pos_arr, index=close.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    rsl_period: int = 135,
    fast_window: int = 5,
    slow_window: int = 20,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        rsl_period=rsl_period,
        fast_window=fast_window,
        slow_window=slow_window,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
