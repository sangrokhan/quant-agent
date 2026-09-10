"""Strategy: Wilder RSI Failure Swing Bottom (bullish reversal confirmation).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per https://fortunetalkstrading.blogspot.com/2022/03/rsi-failure-swing-strategy-explained.html
(J. Welles Wilder's classic RSI Failure Swing): an "advanced" RSI divergence
variant that requires an explicit swing-point BREAK confirmation rather than
just a raw price/RSI divergence. The bullish "Failure Swing Bottom": (1) RSI
makes a low below the oversold level (30), (2) RSI then rallies to a local
swing high (the "fail point"), (3) RSI pulls back to a HIGHER low than the
first low, crucially WITHOUT re-entering oversold territory on this second
low, (4) the buy signal triggers when RSI subsequently breaks back ABOVE the
fail-point swing high. This is a trend-reversal (counter-trend) entry taken
against the prevailing downtrend, per the source. First RSI Failure Swing
strategy in this repo -- distinct from plain RSI oversold-threshold crosses
(30+ prior entries) and raw price/RSI divergence variants, since Failure
Swing requires the specific swing-point break-confirmation structure rather
than just a threshold cross or an unconfirmed divergence.

Signal logic
------------
- RSI(rsi_period) computed via Wilder's standard smoothing.
- Track RSI's own local swing lows/highs via a `swing_window`-bar pivot
  detection (a bar is a swing low/high if it's the min/max within
  +/-swing_window bars).
- State machine per the source's 4-step sequence:
    1. "first_low": RSI swing low occurs with RSI < oversold_level.
    2. "fail_point": subsequent RSI swing high (any level) after the first low.
    3. "second_low": subsequent RSI swing low that is HIGHER than the first
       low AND stays >= oversold_level (did not re-enter oversold).
    4. Entry trigger: RSI closes back above the fail-point value after the
       second_low state is confirmed.
- Exit: RSI crosses back below oversold_level (trend-reversal failed), OR a
  max_hold_days time-stop backstop (added safety net not in the source).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wilder_rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50.0)
    return rsi


def _is_swing_low(series: pd.Series, i: int, window: int) -> bool:
    lo = max(0, i - window)
    hi = min(len(series), i + window + 1)
    if hi - lo < window + 1:
        return False
    return series.iloc[i] == series.iloc[lo:hi].min()


def _is_swing_high(series: pd.Series, i: int, window: int) -> bool:
    lo = max(0, i - window)
    hi = min(len(series), i + window + 1)
    if hi - lo < window + 1:
        return False
    return series.iloc[i] == series.iloc[lo:hi].max()


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    oversold_level: float = 30.0,
    swing_window: int = 3,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    rsi = _wilder_rsi(close, rsi_period)

    n = len(df)
    # NOTE: swing detection at bar i needs swing_window bars of look-ahead
    # within the RSI series to confirm a pivot -- this uses only the RSI
    # series itself (not future close/price data) and is applied causally
    # by only "confirming" a swing swing_window bars after it occurred
    # (i.e. we act on rsi_swing info with an implicit swing_window-bar lag,
    # consistent with how swing points are detected in real-time trading).
    swing_low_flags = [False] * n
    swing_high_flags = [False] * n
    for i in range(n):
        swing_low_flags[i] = _is_swing_low(rsi, i, swing_window)
        swing_high_flags[i] = _is_swing_high(rsi, i, swing_window)

    state = "idle"  # idle -> first_low -> fail_point -> second_low
    first_low_val = None
    fail_point_val = None
    second_low_val = None

    entry_flags = [False] * n
    rsi_vals = rsi.values

    # Confirmation lag: a swing point at bar i is only "known" swing_window
    # bars later.
    for i in range(n):
        confirm_i = i - swing_window
        if confirm_i < 0:
            continue

        if swing_low_flags[confirm_i]:
            val = rsi_vals[confirm_i]
            if state == "idle":
                if val < oversold_level:
                    state = "first_low"
                    first_low_val = val
            elif state == "fail_point":
                if val > first_low_val and val >= oversold_level:
                    state = "second_low"
                    second_low_val = val
                elif val < oversold_level:
                    # re-entered oversold -- reset to a fresh first_low
                    state = "first_low"
                    first_low_val = val
                else:
                    # lower low than first, but still oversold-adjacent -- reset
                    state = "first_low"
                    first_low_val = val

        if swing_high_flags[confirm_i]:
            val = rsi_vals[confirm_i]
            if state == "first_low":
                state = "fail_point"
                fail_point_val = val

        # Entry trigger: RSI breaks back above fail_point_val while in
        # second_low state.
        if state == "second_low" and fail_point_val is not None:
            if rsi_vals[i] > fail_point_val:
                entry_flags[i] = True
                state = "idle"
                first_low_val = None
                fail_point_val = None
                second_low_val = None

    entry_signal = pd.Series(entry_flags, index=df.index)
    exit_signal = rsi < oversold_level

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_days = 0
    entry_vals = entry_signal.values
    exit_vals = exit_signal.fillna(False).values

    for i in range(n):
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
    rsi_period: int = 14,
    oversold_level: float = 30.0,
    swing_window: int = 3,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        rsi_period=rsi_period,
        oversold_level=oversold_level,
        swing_window=swing_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0)
    return strat_ret
