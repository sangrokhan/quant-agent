"""Strategy: Aroon Up/Down crossover (with strength condition) gated by an
ADX trend-strength filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-098):
Per Capital.com's Aroon indicator guide ("A crossover of Aroon up above
Aroon down carries more weight when the crossing line is already above 50
at the point of crossing" and "Pairing Aroon with ADX helps confirm whether
a crossover is occurring in a genuinely trending environment worth
analysing further"), a long entry signal fires when: (1) AroonUp crosses
above AroonDown (a fresh directional flip, not just a threshold state),
(2) AroonUp is already > 50 at the moment of the cross (stronger signal
per the source), AND (3) ADX(14) > adx_threshold (confirms a genuinely
trending, not ranging, market). This is distinct from three prior KB Aroon
entries: 2026-09-04-031 (single Aroon-Down absolute-threshold state, no
crossover event, no ADX), 2026-09-04-063 (Aroon Oscillator
difference-crosses-zero, no strength condition, no ADX), and
2026-09-05-079 (dual-line simultaneous 70/30 threshold STATE, not a
crossover event, no ADX). Here the trigger is a crossover EVENT combined
with an ADX trend-strength gate, which none of the prior three used.

Signal logic
------------
- AroonUp/AroonDown computed over `aroon_window` (default 25, per source).
- ADX computed over `adx_window` (Wilder's standard 14).
- Entry (long): AroonUp crosses above AroonDown on this bar (was <= on
  prior bar) AND AroonUp > 50 at the cross AND ADX > adx_threshold.
- Exit: AroonDown crosses above AroonUp (reverse cross), OR ADX drops back
  below adx_threshold (trend confirmation lost), OR a max_hold_days
  time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py): both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _aroon(high: pd.Series, low: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
    """AroonUp/AroonDown per the standard formula:
    AroonUp = ((window - periods_since_period_high) / window) * 100
    AroonDown = ((window - periods_since_period_low) / window) * 100
    """
    periods_since_high = high.rolling(window + 1).apply(
        lambda x: (window - x.argmax()), raw=True
    )
    periods_since_low = low.rolling(window + 1).apply(
        lambda x: (window - x.argmin()), raw=True
    )
    aroon_up = ((window - periods_since_high) / window) * 100
    aroon_down = ((window - periods_since_low) / window) * 100
    return aroon_up, aroon_down


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    """Wilder's ADX via EMA(alpha=1/window) smoothing (standard Wilder RMA)."""
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(0.0, index=high.index)
    minus_dm = pd.Series(0.0, index=high.index)
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[(down_move > up_move) & (down_move > 0)]

    alpha = 1.0 / window
    atr = tr.ewm(alpha=alpha, adjust=False, min_periods=window).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=alpha, adjust=False, min_periods=window).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=alpha, adjust=False, min_periods=window).mean() / atr)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.ewm(alpha=alpha, adjust=False, min_periods=window).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    aroon_window: int = 25,
    adx_window: int = 14,
    adx_threshold: float = 25.0,
    aroon_up_strength: float = 50.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    aroon_up, aroon_down = _aroon(high, low, aroon_window)
    adx = _adx(high, low, close, adx_window)

    cross_up = (aroon_up > aroon_down) & (aroon_up.shift(1) <= aroon_down.shift(1))
    cross_down = (aroon_down > aroon_up) & (aroon_down.shift(1) <= aroon_up.shift(1))

    entry = cross_up & (aroon_up > aroon_up_strength) & (adx > adx_threshold)
    exit_reverse = cross_down
    exit_trend_lost = adx <= adx_threshold

    entry = entry.fillna(False)
    exit_reverse = exit_reverse.fillna(False)
    exit_trend_lost = exit_trend_lost.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_reverse.iloc[i]) or bool(exit_trend_lost.iloc[i]) or held >= max_hold_days:
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
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
