"""Strategy: VIDYA (Variable Index Dynamic Average, Tushar Chande 1992)
price-crossover-while-sloping trend-following entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-005):
VIDYA is an EMA-style adaptive moving average whose smoothing constant
scales with abs(Chande Momentum Oscillator)/100 at each bar -- high
absolute CMO (strong directional momentum) makes VIDYA track price
quickly (short-EMA-like behavior); low absolute CMO (choppy/ranging
market) makes VIDYA nearly flat (heavily-smoothed, noise-filtering
behavior). Per arrowalgo.com's VIDYA guide, the recommended mechanical
entry is: buy when price crosses above VIDYA while VIDYA is itself sloping
upward (confirms the crossover happens in an active-momentum, not
low-momentum-flat, regime -- the source explicitly warns that crossovers of
a nearly-flat VIDYA "carry no directional information"). Exit when price
crosses below VIDYA while VIDYA is falling, or a max_hold_days time-stop.
First VIDYA strategy in this repo -- explicitly distinguished from KAMA
(2026-09-04-048/151, also Tushar-Chande-family adaptive averages, but using
the Efficiency Ratio for its adaptive scaling factor rather than the Chande
Momentum Oscillator).

Signal logic
------------
- CMO_t = 100 * (sum(up_moves, cmo_period) - sum(down_moves, cmo_period)) /
  (sum(up_moves, cmo_period) + sum(down_moves, cmo_period))
- alpha_t = abs(CMO_t) / 100 * (2 / (vidya_span + 1))  (VIDYA's adaptive
  smoothing constant, scaled by the standard EMA alpha for vidya_span)
- VIDYA_t = VIDYA_{t-1} + alpha_t * (close_t - VIDYA_{t-1})  (seed VIDYA_0
  = close_0)
- Entry (long): close crosses above VIDYA AND VIDYA is sloping upward
  (VIDYA_t > VIDYA_{t-1}).
- Exit: close crosses below VIDYA AND VIDYA is sloping downward, OR a
  max_hold_days time-stop backstop (VIDYA gives no explicit stop rule when
  a trend just goes flat without a clean reverse cross).
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


def _chande_momentum_oscillator(close: pd.Series, cmo_period: int) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    sum_up = up.rolling(cmo_period, min_periods=max(2, cmo_period // 2)).sum()
    sum_down = down.rolling(cmo_period, min_periods=max(2, cmo_period // 2)).sum()
    denom = (sum_up + sum_down).replace(0.0, pd.NA)
    cmo = 100.0 * (sum_up - sum_down) / denom
    return cmo.fillna(0.0)


def _vidya(close: pd.Series, cmo_period: int, vidya_span: int) -> pd.Series:
    cmo = _chande_momentum_oscillator(close, cmo_period)
    base_alpha = 2.0 / (vidya_span + 1.0)
    scale = cmo.abs() / 100.0
    alpha = (scale * base_alpha).clip(lower=0.0, upper=1.0)

    vidya = pd.Series(index=close.index, dtype=float)
    vidya.iloc[0] = close.iloc[0]
    for i in range(1, len(close)):
        a = alpha.iloc[i]
        if pd.isna(a):
            a = 0.0
        vidya.iloc[i] = vidya.iloc[i - 1] + a * (close.iloc[i] - vidya.iloc[i - 1])
    return vidya


def generate_signals(
    price_df: pd.DataFrame,
    cmo_period: int = 9,
    vidya_span: int = 14,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    vidya = _vidya(close, cmo_period, vidya_span)
    vidya_slope_up = vidya.diff() > 0
    vidya_slope_down = vidya.diff() < 0

    above = close > vidya
    cross_up = above & (~above.shift(1).fillna(False))
    cross_down = (~above) & above.shift(1).fillna(False)

    entry = cross_up & vidya_slope_up.fillna(False)
    exit_signal = cross_down & vidya_slope_down.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
