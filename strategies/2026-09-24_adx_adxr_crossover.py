"""Strategy: ADX crosses above/below its own smoothed sibling ADXR
(the "ADX vs ADXR crossover" trend-acceleration signal).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-018):
Per a Google AI-overview synthesis (TradingPedia/alphasquare.co.kr/Linnsoft
consensus explainers) of ADXR trading strategies: "ADX crossing above ADXR
(the smoother line) signals trend acceleration -- buy; ADX crossing below
ADXR signals momentum weakening -- exit/avoid directional trades." This is
distinct from this repo's 6 prior ADXR entries: 2026-09-07-013 tested ADXR
as a discrete THRESHOLD-crossing confirmation (rejected); 2026-09-16-054
reframed ADXR itself as a CONTINUOUS SIZING dial (accepted, full universe);
2026-09-22-026/027 combined ADXR multiplicatively with a separate ATR
volatility term into a Commodity Selection Index (both rejected). None
tested the two-line ADX-vs-its-own-ADXR crossover construction that this
source specifically describes -- a distinct trigger mechanism (line cross,
not threshold cross or continuous rescale).

Signal logic
------------
- Wilder's ADX(adx_period) on high/low/close (standard +DI/-DI/DX/ADX
  recursive smoothing).
- ADXR[t] = (ADX[t] + ADX[t - adx_period]) / 2 (Wilder's own definition:
  average the current ADX with the ADX value adx_period bars ago).
- Entry (long): ADX crosses above ADXR (trend accelerating), gated by
  +DI > -DI (directional confirmation, source's own stated companion rule
  for the plain trend-filter variant, carried over here since a bare
  ADX>ADXR cross with no directional confirmation would trade both up and
  down accelerations identically).
- Exit: ADX crosses below ADXR (momentum weakening), OR a max_hold_days
  time-stop as a safety net.

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


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _adx_di(df: pd.DataFrame, period: int):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(0.0, index=df.index)
    minus_dm = pd.Series(0.0, index=df.index)
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[(down_move > up_move) & (down_move > 0)]

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    atr = _wilder_smooth(tr, period)
    plus_di = 100.0 * _wilder_smooth(plus_dm, period) / atr.replace(0, pd.NA)
    minus_di = 100.0 * _wilder_smooth(minus_dm, period) / atr.replace(0, pd.NA)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    adx = _wilder_smooth(dx.fillna(0.0), period)

    return adx, plus_di.fillna(0.0), minus_di.fillna(0.0)


def _adxr(adx: pd.Series, period: int) -> pd.Series:
    return (adx + adx.shift(period)) / 2.0


def generate_signals(
    price_df: pd.DataFrame,
    adx_period: int = 14,
    max_hold_days: int = 40,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0,leverage_cap} long/flat position series.

    ``leverage_cap`` scales the binary long/flat exposure (default 1.0 =
    full exposure, matching original behavior). Added for a crypto MDD
    leverage-cap-recalibration follow-up -- see
    knowledge_base/strategies_log.jsonl id 2026-09-24-018 (decisive MDD
    failure on BTC/USDT and ETH/USDT at leverage_cap=1.0).
    """
    df = _prep(price_df)
    close = df["close"]

    adx, plus_di, minus_di = _adx_di(df, adx_period)
    adxr = _adxr(adx, adx_period)

    above = adx > adxr
    prev_above = above.shift(1).fillna(False)
    cross_up = above & (~prev_above)

    below = adx < adxr
    prev_below = below.shift(1).fillna(True)
    cross_down = below & (~prev_below)

    di_confirm = plus_di > minus_di
    entry = cross_up & di_confirm.fillna(False)

    position = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0.0
                continue
            position.iloc[i] = leverage_cap
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = leverage_cap
            else:
                position.iloc[i] = 0.0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
