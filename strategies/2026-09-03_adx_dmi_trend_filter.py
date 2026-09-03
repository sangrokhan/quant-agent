"""Strategy: ADX/DMI trend-strength-filtered directional crossover, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-017):
Source: Google search snippets converging across multiple sites (Reddit
r/algotrading, TradingView, FXNX, Fazen Capital, DXP Analytics) for the
classic Wilder DMI/ADX trading rule -- web_search backend intermittently
failing this cron trigger, used browser_exec Google search directly.
Concrete rule found: ADX(14) must be above 25 (confirms a tradeable trend,
vs range-bound/choppy below 20-25) AND +DI (positive directional index)
crosses above -DI (negative directional index) for a long entry.

This is the first DMI/ADX-directional-index strategy tested in this repo --
distinct from every prior trend/momentum construction (SMA crossover -001,
Bollinger meanrev/squeeze -001/-011, trailing-return momentum -002/-003/
-004/-012, RSI2 meanrev -005, Donchian breakout -008, MACD signal-cross
-013, SuperTrend -014, Keltner breakout -016, 52wk-high proximity -015)
because ADX/DMI explicitly decomposes trend STRENGTH (ADX magnitude) from
trend DIRECTION (+DI vs -DI relative position), using it as an orthogonal
"is this worth trading at all" filter layered on top of a directional
crossover trigger, rather than a single combined price/return/band signal.

Signal logic (long-only, per SAFETY.md -- no short leg even though DMI is
naturally bidirectional)
------------
- +DM, -DM, ATR/TR computed per Wilder's standard DMI formulas.
- +DI = 100 * smoothed(+DM) / smoothed(TR); -DI = 100 * smoothed(-DM) / smoothed(TR)
- DX = 100 * |+DI - -DI| / (+DI + -DI); ADX = smoothed(DX)
- Entry (long): ADX > adx_threshold AND +DI crosses above -DI (this bar
  +DI > -DI, previous bar +DI <= -DI).
- Exit: -DI crosses above +DI (this bar -DI > +DI, previous bar -DI <= +DI),
  OR ADX drops back below adx_threshold (trend strength lost).
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


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    # Wilder's smoothing == an EMA with alpha = 1/period.
    return series.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _dmi_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int):
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(0.0, index=high.index)
    minus_dm = pd.Series(0.0, index=high.index)
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[(down_move > up_move) & (down_move > 0)]

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = _wilder_smooth(tr, period)
    plus_dm_smooth = _wilder_smooth(plus_dm, period)
    minus_dm_smooth = _wilder_smooth(minus_dm, period)

    plus_di = 100.0 * (plus_dm_smooth / atr.replace(0, pd.NA))
    minus_di = 100.0 * (minus_dm_smooth / atr.replace(0, pd.NA))

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    adx = _wilder_smooth(dx.fillna(0.0), period)

    return plus_di, minus_di, adx


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 14,
    adx_threshold: float = 25.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    plus_di, minus_di, adx = _dmi_adx(high, low, close, period)

    plus_above = plus_di > minus_di
    prev_plus_above = plus_above.shift(1).fillna(False)
    bull_cross = plus_above & (~prev_plus_above)
    bear_cross = (~plus_above) & prev_plus_above

    strong_trend = adx > adx_threshold

    entry = bull_cross & strong_trend
    exit_signal = bear_cross | (~strong_trend)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
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
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
