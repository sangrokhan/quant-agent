"""Strategy: Relative Vigor Index (RVI) signal-line crossover, gated by a
200-day SMA trend filter (per the source's own explicit warning that a
naive crossover-only version suffers frequent whipsaw in ranging markets).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-034):
Source: Google AI Overview synthesis (Korean-language SERP; search
"Relative Vigor Index RVI signal line crossover strategy specific rule
backtest"), read via browser_exec Google SERP fallback (web_search DDGS
backend errored this iteration). Disclosed rule set:
  - RVI(10): (close - open) smoothed via a 4-bar symmetrically-weighted
    moving average (SWMA, weights [1,2,2,1]/6), divided by (high - low)
    similarly smoothed, summed over a 10-bar window (standard RVI formula).
  - Signal line: 4-period SWMA of RVI itself.
  - Entry: RVI crosses above the signal line (bullish crossover).
  - Exit: RVI crosses back below the signal line (bearish crossover).
  - Source's own explicit caveat: naive crossover-only trading suffers
    frequent whipsaw losses in choppy/ranging markets; recommends
    combining with a trend filter (moving average or ADX) "for viability".
    This implementation follows that recommendation directly, adding a
    200-day SMA trend filter (price above 200 SMA = bullish regime
    required for entry) rather than testing the admittedly-flawed naive
    version the source itself already predicts will fail.
No prior entry in this KB uses "RVI signal line" (checked via
strategies_index.jsonl grep: "RVI signal line" had zero prior matches; 11
generic "Relative Vigor Index" mentions use different mechanisms, e.g.
zero-line crosses or divergence, not this specific signal-line-crossover +
200-SMA-trend-filter combo).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _swma4(series: pd.Series) -> pd.Series:
    """Symmetrically-weighted 4-bar moving average, weights [1,2,2,1]/6."""
    w1 = series.shift(3)
    w2 = series.shift(2)
    w3 = series.shift(1)
    w4 = series
    return (w1 * 1 + w2 * 2 + w3 * 2 + w4 * 1) / 6.0


def _rvi(df: pd.DataFrame, window: int) -> pd.Series:
    co = df["close"] - df["open"]
    hl = df["high"] - df["low"]
    co_smooth = _swma4(co)
    hl_smooth = _swma4(hl)
    numerator = co_smooth.rolling(window).sum()
    denominator = hl_smooth.rolling(window).sum().replace(0.0, pd.NA)
    return (numerator / denominator).fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    rvi_window: int = 10,
    trend_sma_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rvi = _rvi(df, rvi_window)
    signal = _swma4(rvi)

    sma = close.rolling(trend_sma_window, min_periods=max(20, trend_sma_window // 4)).mean()
    bullish_regime = close > sma

    bull_cross = (rvi > signal) & (rvi.shift(1) <= signal.shift(1))
    bear_cross = (rvi < signal) & (rvi.shift(1) >= signal.shift(1))

    entry = bull_cross & bullish_regime

    pos_vals = []
    in_pos = False
    for i in range(len(close)):
        if not in_pos and bool(entry.iloc[i]):
            in_pos = True
        elif in_pos and bool(bear_cross.iloc[i]):
            in_pos = False
        pos_vals.append(1 if in_pos else 0)

    return pd.Series(pos_vals, index=close.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    rvi_window: int = 10,
    trend_sma_window: int = 200,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, rvi_window=rvi_window, trend_sma_window=trend_sma_window
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = (position.shift(1).fillna(0) * daily_ret).fillna(0.0)
    return strat_ret
