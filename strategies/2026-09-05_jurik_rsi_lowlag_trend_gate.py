"""Strategy: Jurik-style low-lag RSI (RSX approximation) with trend gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-087),
sourced from https://alphax.trading/dictionary/jurik-rsi (AlphaX Quant
Library, "Jurik RSI: Advanced Momentum Analysis for Quant Traders"): the
Jurik RSI (Mark Jurik's RSX) replaces the Wilder/EMA smoothing inside a
standard RSI with a lower-lag adaptive filter (Jurik Moving Average, JMA)
applied separately to positive and negative price deltas, producing a
smoother, less noisy 0-100 oscillator that gives more reliable
overbought/oversold crossings than plain RSI. The source's own disclosed
formula is:
    RSI_Numerator   = JMA(Positive_Delta, Length)
    RSI_Denominator = JMA(Positive_Delta, Length) + JMA(Negative_Delta, Length)
    Jurik_RSI = 100 * Numerator / Denominator
The exact proprietary JMA phase/power parameters aren't disclosed for
free, so this implementation approximates the "reduced-lag adaptive
smoothing" property with a DEMA (double-EMA, a standard, well-documented
zero-lag-reduction technique: DEMA = 2*EMA(x) - EMA(EMA(x))) applied to
the positive/negative deltas in place of JMA -- capturing the same
architectural idea (lag-reduced smoothing of the RSI's raw gain/loss
components, rather than Wilder's plain EMA) without claiming to
reverse-engineer Jurik's exact algorithm.

The source's own "Execution Rules for Systematic Traders" are used
directly:
    - Enter long when the (Jurik-style) RSI crosses above 30 from below,
      "during a confirmed uptrend" (operationalized here as close above a
      `trend_window`-period SMA, per the source's own "secondary filter,
      such as a long-term trend indicator" recommendation).
    - Exit long when the RSI reaches/crosses above 70 (momentum peaked),
      or the trend filter breaks, or after `max_hold_days` (this repo's
      standard safety time-stop, not explicitly in the source).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _dema(series: pd.Series, span: int) -> pd.Series:
    ema1 = series.ewm(span=span, adjust=False, min_periods=span).mean()
    ema2 = ema1.ewm(span=span, adjust=False, min_periods=span).mean()
    return 2 * ema1 - ema2


def _jurik_style_rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    pos_delta = delta.clip(lower=0)
    neg_delta = -delta.clip(upper=0)

    smoothed_pos = _dema(pos_delta, length).clip(lower=0)
    smoothed_neg = _dema(neg_delta, length).clip(lower=0)

    denom = smoothed_pos + smoothed_neg
    rsi = 100 * (smoothed_pos / denom.replace(0, pd.NA))
    return rsi.astype(float)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_length: int = 14,
    oversold_threshold: float = 30.0,
    overbought_threshold: float = 70.0,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _jurik_style_rsi(close, rsi_length)
    sma_trend = close.rolling(trend_window, min_periods=trend_window).mean()
    above_trend = close > sma_trend

    crossed_up = (rsi > oversold_threshold) & (rsi.shift(1) <= oversold_threshold)
    crossed_overbought = (rsi >= overbought_threshold) & (rsi.shift(1) < overbought_threshold)

    entry_event = crossed_up.fillna(False) & above_trend.fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0
    entry_arr = entry_event.values
    exit_arr = crossed_overbought.fillna(False).values
    above_trend_arr = above_trend.fillna(False).values

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if exit_arr[i] or (not above_trend_arr[i]) or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_arr[i]:
                in_position = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
