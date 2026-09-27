"""Strategy: Intraday Range-Efficiency trend-day regime gate + SMA trend.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-078):
Per thetrading.tools' "Range Efficiency" tool
(https://www.thetrading.tools/range-efficiency, read via browser_exec this
iteration), a per-bar "range efficiency" metric = |close-open| / (high-low)
measures how much of a single day's full intraday range converted into net
directional progress: values near 1 = clean trend day (open->close move
captured most of the day's range), values near 0 = choppy day that
travelled a lot but closed near the open. The source's own 50-day average
of this ratio is used as a trend-vs-chop REGIME gauge (rising = cleaner
trending tape, falling = more chop/whipsaw). This is a genuinely distinct
formula from this repo's existing Kaufman Efficiency Ratio family (net
multi-bar closing-price change / sum of multi-bar absolute changes -- a
MULTI-BAR trend-strength measure) and from Ehlers/FRAMA fractal-dimension
efficiency variants already tested here -- this is a purely intrabar,
single-day open/high/low/close ratio, averaged over a rolling window as a
regime filter.

Adapted here as a testable single-asset rule: gate a standard SMA
trend-following signal (long when close > SMA(trend_window)) to only take
new entries while the rolling N-day average range-efficiency is ABOVE its
own regime threshold (i.e. only trend-follow when the tape itself has
recently been producing "clean trend days", per the source's own stated
interpretation that a rising range-efficiency average means "the tape is
producing cleaner trends" -- a better environment for trend-following).

Signal logic
------------
- Per-bar range efficiency: eff[i] = |close[i]-open[i]| / (high[i]-low[i])
  (0 when high==low, to avoid divide-by-zero).
- Rolling eff_window-day average of eff -> regime signal.
- Entry (long): close > SMA(trend_window) AND rolling_avg_eff >=
  eff_threshold (trending/clean-tape regime).
- Exit: close < SMA(trend_window) OR rolling_avg_eff < eff_threshold
  (regime flips choppy).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    eff_window: int = 50,
    eff_threshold: float = 0.474,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    trend_window: SMA lookback for the base trend-following signal.
    eff_window: rolling lookback for the range-efficiency regime average.
    eff_threshold: minimum rolling-average range-efficiency required to
        allow new/continued long exposure (source's own disclosed all-time
        QQQ average is ~0.474, used as the default threshold).
    """
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]

    rng = (high - low).replace(0, pd.NA)
    eff = (close - open_).abs() / rng
    eff = eff.fillna(0.0)
    rolling_eff = eff.rolling(eff_window).mean()

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma
    clean_regime = rolling_eff >= eff_threshold

    position = (trend_up & clean_regime).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
