"""Strategy: MACD-V (Volatility-Normalized MACD, Alex Spiroglou 2022)
"Rebounding" momentum-stage entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-094),
sourced from
https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-v
("MACD-V = [(12-period EMA - 26-period EMA) / ATR(26)] * 100. Signal line
= 9-period EMA of MACD-V. ... Rebounding. The market is rebounding and
rising off a low when the MACD-V is between 50 and -150 (50 > X > -150)
and above its signal line."):

First strategy in this repo using a volatility-NORMALIZED MACD (divided by
ATR(26), producing a boundless-but-comparable-across-time/assets
momentum reading) rather than plain price-difference MACD (already
extensively tested: 2026-09-03-013 plain MACD, 2026-09-04-... histogram
reversal, RSI dual confirmation, zeroline confirm, VW-MACD, Elder Impulse,
etc.) -- MACD-V's core innovation is dividing by ATR so the same numeric
threshold (e.g. entering "Rebounding" territory) is meaningful across
different symbols/vol regimes, addressing this repo's frequent finding
that plain-MACD-family strategies need per-symbol/per-regime threshold
tuning.

Signal logic
------------
- MACD-V = ((EMA(close,12) - EMA(close,26)) / ATR(close,26)) * 100.
- Signal line = EMA(MACD-V, 9).
- Long entry: MACD-V crosses above its signal line while MACD-V is in the
  "Rebounding" zone (entry_low < MACD-V < entry_high, source's exact
  range -150 to 50 -- i.e. off a low but not yet in "Rallying"/overbought
  territory).
- Exit: MACD-V crosses back below its signal line, OR MACD-V rises above
  overbought_level (150, source's "Risk (overbought)" stage), OR a
  max_hold_days time-stop (repo standard safety valve).

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


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    tr = _true_range(df)
    return tr.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()


def _macd_v(df: pd.DataFrame, fast: int, slow: int, atr_window: int) -> pd.Series:
    close = df["close"]
    ema_fast = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
    atr = _atr(df, atr_window)
    macd_v = ((ema_fast - ema_slow) / atr) * 100
    return macd_v


def generate_signals(
    price_df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    atr_window: int = 26,
    signal_span: int = 9,
    entry_low: float = -150.0,
    entry_high: float = 50.0,
    overbought_level: float = 150.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    macd_v = _macd_v(df, fast, slow, atr_window)
    signal = macd_v.ewm(span=signal_span, adjust=False, min_periods=signal_span).mean()

    crossed_up = (macd_v > signal) & (macd_v.shift(1) <= signal.shift(1))
    crossed_down = (macd_v < signal) & (macd_v.shift(1) >= signal.shift(1))

    in_rebound_zone = (macd_v > entry_low) & (macd_v < entry_high)
    entry_signal = (crossed_up & in_rebound_zone).fillna(False).values
    exit_signal = (crossed_down | (macd_v > overbought_level)).fillna(False).values

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if exit_signal[i] or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_signal[i]:
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
