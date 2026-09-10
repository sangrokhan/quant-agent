"""Strategy: Zero Lag MACD signal-line crossover, gated by an SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per https://www.quantifiedstrategies.com/zero-lag-macd/ (John Ehlers & Rick
Way's Zero Lag MACD): the classic MACD line/signal-line crossover mechanic is
applied to *de-lagged* ("zero-lag") EMAs instead of plain EMAs, computed via
the disclosed double-EMA "de-lag" trick (EMA of an EMA, then extrapolate by
the difference) applied at both the short/long EMA stage and again at the
signal-line stage. The zero-lag MACD line crossing above its zero-lag signal
line signals a long entry (momentum turning up faster than classic MACD
would show); crossing back below signals exit. The source's own caveat is
that the increased sensitivity that removes lag also makes it more prone to
whipsaws in sideways/non-trending markets -- so this implementation adds an
SMA(trend_window) trend filter (only take crossover-longs while
close > SMA(trend_window)) to filter out exactly the regime the source warns
about. First Zero Lag MACD strategy tested in this repo (MACD family has many
prior variants -- classic MACD histogram/divergence -- but none use the
Ehlers/Way zero-lag EMA construction).

Signal logic
------------
- ZeroLagEMA(period) = EMA1 + (EMA1 - EMA2), where EMA1 = EMA(close, period)
  and EMA2 = EMA(EMA1, period) -- the source's disclosed de-lag formula.
- Zero Lag MACD = ZeroLagEMA(fast_period) - ZeroLagEMA(slow_period).
- Zero Lag Signal = ZeroLagEMA-style de-lag applied to the MACD line itself,
  using signal_period (i.e. Signal1 = EMA(MACD, signal_period),
  Signal2 = EMA(Signal1, signal_period), Signal = Signal1 + (Signal1-Signal2)).
- Entry (long): Zero Lag MACD crosses above Zero Lag Signal AND
  close > SMA(trend_window) (trend filter, source's own caveat).
- Exit: Zero Lag MACD crosses back below Zero Lag Signal, OR the trend
  filter breaks (close <= SMA(trend_window)), OR a max_hold_days time-stop
  backstop (avoid indefinite holds through a single long crossover regime).

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


def _zero_lag_ema(series: pd.Series, period: int) -> pd.Series:
    ema1 = series.ewm(span=period, adjust=False).mean()
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    return ema1 + (ema1 - ema2)


def generate_signals(
    price_df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    zl_fast = _zero_lag_ema(close, fast_period)
    zl_slow = _zero_lag_ema(close, slow_period)
    zl_macd = zl_fast - zl_slow

    zl_signal = _zero_lag_ema(zl_macd, signal_period)

    trend_sma = close.rolling(trend_window).mean()
    trend_ok = close > trend_sma

    bull_cross = (zl_macd > zl_signal) & (zl_macd.shift(1) <= zl_signal.shift(1))
    bear_cross = (zl_macd < zl_signal) & (zl_macd.shift(1) >= zl_signal.shift(1))

    entry_signal = bull_cross & trend_ok

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_days = 0
    entry_signal_vals = entry_signal.values
    bear_cross_vals = bear_cross.values
    trend_ok_vals = trend_ok.values

    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            exit_now = bear_cross_vals[i] or (not trend_ok_vals[i]) or (hold_days >= max_hold_days)
            if exit_now:
                in_pos = False
                hold_days = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_signal_vals[i]:
                in_pos = True
                hold_days = 0
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0)
    return strat_ret
