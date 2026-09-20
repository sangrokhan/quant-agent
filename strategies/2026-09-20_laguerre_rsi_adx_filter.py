"""Strategy: Laguerre RSI (Ehlers) crossover, filtered by ADX trend-strength gate.

Hypothesis (see knowledge_base/strategies_log.jsonl, this entry's id):
Per Sword Red's "Laguerre RSI with ADX Filtered Trading Signals Strategy"
(https://medium.com/@redsword_23261/laguerre-rsi-with-adx-filtered-trading-signals-strategy-cb7ab0c02694,
read via browser_exec after web_extract's DDGS backend refused extraction),
a fast momentum oscillator (4-stage recursive Laguerre filter -> RSI-style
[0,1] oscillator, alpha=0.2 default) crossing above a buy_level (20 on a
0-100 scale) signals a momentum shift worth trading LONG, but only when
ADX confirms the market is trending (ADX > adx_level, default 20) --
avoiding false crossovers in choppy/range-bound conditions. Exit when the
Laguerre RSI crosses back below sell_level (80) OR ADX drops back below
adx_level (trend weakening / no longer confirmed), or after a max holding
period as a safety backstop.

This repo has 15+ prior Laguerre RSI entries (mostly standalone
oversold-recovery / zero-line / continuous-sizing variants -- e.g.
2026-09-05-053, 2026-09-06-110, 2026-09-16-138, 2026-09-14-198) but NONE
combine it with an ADX trend-strength confirmation gate the way the source
article does -- this is a distinct dual-indicator confirmation design
(fast oscillator entry timing + slow trend-strength filter), not a
standalone Laguerre RSI threshold trigger.

Signal logic
------------
- Laguerre RSI (LaRSI): 4-stage recursive Laguerre filter cascade (gamma =
  1 - alpha) applied to close; cu/cd = sum of up/down differences across
  stages; LaRSI = cu / (cu + cd), bounded [0, 1] by construction.
- ADX(adx_length): standard Wilder average directional index computed from
  +DI/-DI (no external TA lib -- implemented directly from OHLC).
- Entry (long): LaRSI * 100 crosses above buy_level AND ADX > adx_level.
- Exit: LaRSI * 100 crosses below sell_level, OR ADX drops back to/below
  adx_level (trend confirmation lost), OR max_hold_days elapses.
- Flat otherwise.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _laguerre_rsi(close: pd.Series, alpha: float = 0.2) -> pd.Series:
    """4-stage recursive Laguerre filter -> [0,1] RSI-style oscillator."""
    gamma = 1.0 - alpha
    n = len(close)
    vals = close.values
    l0 = [0.0] * n
    l1 = [0.0] * n
    l2 = [0.0] * n
    l3 = [0.0] * n
    larsi = [0.0] * n
    for i in range(n):
        prev_l0 = l0[i - 1] if i > 0 else 0.0
        prev_l1 = l1[i - 1] if i > 0 else 0.0
        prev_l2 = l2[i - 1] if i > 0 else 0.0
        prev_l3 = l3[i - 1] if i > 0 else 0.0
        l0[i] = (1 - gamma) * vals[i] + gamma * prev_l0
        l1[i] = -gamma * l0[i] + prev_l0 + gamma * prev_l1
        l2[i] = -gamma * l1[i] + prev_l1 + gamma * prev_l2
        l3[i] = -gamma * l2[i] + prev_l2 + gamma * prev_l3
        cu = (l0[i] - l1[i] if l0[i] > l1[i] else 0.0) \
            + (l1[i] - l2[i] if l1[i] > l2[i] else 0.0) \
            + (l2[i] - l3[i] if l2[i] > l3[i] else 0.0)
        cd = (l1[i] - l0[i] if l0[i] < l1[i] else 0.0) \
            + (l2[i] - l1[i] if l1[i] < l2[i] else 0.0) \
            + (l3[i] - l2[i] if l2[i] < l3[i] else 0.0)
        denom = cu + cd
        larsi[i] = 0.0 if denom == 0 else cu / denom
    return pd.Series(larsi, index=close.index)


def _adx(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """Wilder's ADX from high/low/close."""
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
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean() / atr)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float("nan"))
    adx = dx.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    return adx.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    alpha: float = 0.2,
    buy_level: float = 20.0,
    sell_level: float = 80.0,
    adx_length: int = 14,
    adx_level: float = 20.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    larsi = _laguerre_rsi(close, alpha=alpha) * 100.0
    adx = _adx(df, length=adx_length)

    larsi_prev = larsi.shift(1)
    cross_up = (larsi > buy_level) & (larsi_prev <= buy_level)
    cross_down = (larsi < sell_level) & (larsi_prev >= sell_level)
    trend_ok = adx > adx_level

    entry = cross_up & trend_ok
    exit_signal = cross_down | (~trend_ok)

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
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
