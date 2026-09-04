"""Strategy: Twiggs Money Flow (TMF) zero-line crossover as a pullback-end
timing signal within an established uptrend.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-002):
Twiggs Money Flow (Colin Twiggs, refinement of Chaikin Money Flow that
weights volume by the close's position within the *True* Range -- including
gaps -- rather than the plain high-low range) gives a bullish zero-line
crossover when buying pressure (volume-weighted) turns positive. Per
quantifiedstrategies.com's TMF article, the indicator is explicitly
recommended for "timing the end of a pullback in a trending market": during
an uptrend's pullback, TMF prints mostly negative readings, and the first
positive reading (zero-line cross from below) is the suggested long signal.
This is tested here as a mechanical trend-filtered zero-line-crossover rule
(source's own numeric backtest rule itself was paywalled) -- first Twiggs
Money Flow strategy in this repo (distinct from CMF, which it's explicitly a
refinement of, and from AD-line/OBV/PVT, the other volume-accumulation
indicators already tested).

Signal logic
------------
- True High (TH) = max(high, prev_close); True Low (TL) = min(low, prev_close)
  (captures gaps, unlike a plain high-low range).
- TRCL_t = (2*close_t - TL_t - TH_t) / (TH_t - TL_t)  (close's position
  within the true range, scaled to [-1, 1]; 0 when TH==TL).
- Range Volume = EMA(volume * TRCL, tmf_window)
- TMF = 100 * Range Volume / EMA(volume, tmf_window)   (tmf_window default 21,
  the source's stated canonical default)
- trend_filter: close > close.rolling(trend_window).mean() (uptrend gate,
  matching the source's own "pullback within a trend" framing rather than
  trading the zero-cross standalone in any regime).
- Entry (long): TMF crosses from <= 0 to > 0 (bullish zero-line cross) AND
  trend_filter is true.
- Exit: TMF crosses back below zero, OR trend_filter flips false, OR a
  max_hold_days time-stop backstop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _twiggs_money_flow(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, tmf_window: int
) -> pd.Series:
    prev_close = close.shift(1)
    true_high = pd.concat([high, prev_close], axis=1).max(axis=1)
    true_low = pd.concat([low, prev_close], axis=1).min(axis=1)
    tr_range = (true_high - true_low).replace(0.0, pd.NA)

    trcl = (2 * close - true_low - true_high) / tr_range
    trcl = trcl.fillna(0.0)

    range_volume = (volume * trcl).ewm(span=tmf_window, adjust=False).mean()
    vol_ema = volume.ewm(span=tmf_window, adjust=False).mean().replace(0.0, pd.NA)
    tmf = 100.0 * range_volume / vol_ema
    return tmf.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    tmf_window: int = 21,
    trend_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]

    tmf = _twiggs_money_flow(high, low, close, volume, tmf_window)
    trend_ma = close.rolling(trend_window, min_periods=max(5, trend_window // 5)).mean()
    trend_ok = close > trend_ma

    tmf_positive = tmf > 0
    zero_cross_up = tmf_positive & (~tmf_positive.shift(1).fillna(False))

    entry = zero_cross_up & trend_ok.fillna(False)
    exit_cross = (~tmf_positive) | (~trend_ok.fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or held >= max_hold_days:
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
    daily_ret = position.shift(1).fillna(0) * close.pct_change().fillna(0.0)
    return daily_ret
