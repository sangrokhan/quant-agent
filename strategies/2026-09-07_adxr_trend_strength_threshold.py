"""Strategy: ADXR (Average Directional Movement Rating) trend-strength
threshold-crossing confirmation, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-013):
Per forex-indicators.net's ADXR page: ADXR is Wilder's ADX further smoothed
via a "rating" -- the average of the current ADX and the ADX from
`adxr_lag` periods ago -- making it react more slowly to short-term
reversals than raw ADX. The source's own rule: "When ADXR is above 25, use
a trend-following system... a rising ADXR, with +DI above -DI, indicates a
strengthening bullish market." Operationalized here as a threshold-CROSSING
entry trigger (ADXR crossing up through 25) confirmed by the DI direction
already being bullish, rather than the DI-crossover-style entry trigger this
repo already tested (2026-09-03-017's ADX/DMI directional crossover,
rejected). This is a meaningfully different mechanism: ADXR is a smoothed
"rating" of trend strength (average of two ADX readings separated by a lag),
not raw ADX, and the entry event here is the smoother rating crossing a
strength threshold while direction is already confirmed, vs. the prior
strategy's DI-crossover trigger gated by raw-ADX magnitude.

Signal logic (long-only, per SAFETY.md)
------------
- +DM, -DM, ATR/TR, +DI, -DI, ADX computed per Wilder's standard DMI
  formulas (adx_window periods).
- ADXR[t] = (ADX[t] + ADX[t - adxr_lag]) / 2.
- Entry (long): ADXR crosses above adxr_threshold (this bar ADXR >
  threshold, previous bar ADXR <= threshold) AND +DI > -DI at entry (source's
  "rising ADXR with +DI above -DI" bullish confirmation).
- Exit: ADXR drops back below adxr_threshold, OR -DI crosses above +DI,
  OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def _wilder_smooth(series: pd.Series, window: int) -> pd.Series:
    return series.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    adx_window: int = 14,
    adxr_lag: int = 14,
    adxr_threshold: float = 25.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = _wilder_smooth(tr, adx_window)
    plus_di = 100 * _wilder_smooth(plus_dm, adx_window) / atr
    minus_di = 100 * _wilder_smooth(minus_dm, adx_window) / atr

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = _wilder_smooth(dx, adx_window)
    adxr = (adx + adx.shift(adxr_lag)) / 2.0

    bullish_dir = plus_di > minus_di
    entry = (adxr > adxr_threshold) & (adxr.shift(1) <= adxr_threshold) & bullish_dir
    exit_strength = adxr < adxr_threshold
    exit_dir_flip = minus_di > plus_di

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_hit = bool(exit_strength.iloc[i]) or bool(exit_dir_flip.iloc[i])
            if exit_hit or held >= max_hold_days:
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
