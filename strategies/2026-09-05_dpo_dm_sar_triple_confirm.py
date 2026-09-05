"""Strategy: DPO + Directional Movement (+DM/-DM) + Parabolic SAR triple
confirmation trend entry, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-062):
Per FBS.eu's "ADX and DPO strategy" (Google search snippet, source page
itself 404'd): a long entry requires THREE simultaneous confirmations —
(1) the Detrended Price Oscillator (DPO) crosses above its zero line
(cyclical momentum turning positive), (2) the +DM (positive directional
movement) line crosses above -DM (directional trend strength confirms
upside), and (3) Parabolic SAR flips from above price to below price
(trend-following stop-and-reverse also turns bullish). This is a distinct
construction from every prior DPO/ADX/SAR strategy in this repo: plain DPO
zero-cross (2026-09-04-056, accepted) uses DPO alone with no ADX/SAR gate;
plain Parabolic SAR (2026-09-04-042, accepted QQQ only) uses only the SAR
flip + a slow SMA trend filter, no DPO or +DM/-DM; no prior strategy
requires all three (cyclical + directional + stop-reversal) signals to fire
on the same bar.

Signal logic
------------
- DPO = close - SMA(dpo_window) shifted back by dpo_window//2 + 1 bars
  (standard detrending construction).
- +DM/-DM/ADX via Wilder's smoothing (di_window).
- Parabolic SAR via the classic Wilder algorithm (af_start, af_step,
  af_max).
- Long entry: DPO crosses from <=0 to >0 AND +DI crosses above -DI AND SAR
  is below price (bullish state) -- all three true simultaneously on entry
  bar (not necessarily crossing on the exact same bar for SAR/DI, but all
  three conditions must hold on the entry bar per the source's "wait for
  all three" framing).
- Exit: SAR flips back above price (bearish reversal), or a max_hold_days
  time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _dpo(close: pd.Series, window: int) -> pd.Series:
    shift = window // 2 + 1
    sma = close.rolling(window).mean()
    return close - sma.shift(shift)


def _directional_movement(df: pd.DataFrame, window: int):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1 / window, adjust=False).mean()
    plus_dm_smooth = pd.Series(plus_dm, index=df.index).ewm(alpha=1 / window, adjust=False).mean()
    minus_dm_smooth = pd.Series(minus_dm, index=df.index).ewm(alpha=1 / window, adjust=False).mean()

    plus_di = 100 * (plus_dm_smooth / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm_smooth / atr.replace(0, np.nan))
    return plus_di.fillna(0.0), minus_di.fillna(0.0)


def _parabolic_sar(df: pd.DataFrame, af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.20) -> pd.Series:
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    n = len(df)
    sar = np.zeros(n)
    if n == 0:
        return pd.Series(sar, index=df.index)

    uptrend = True
    af = af_start
    ep = high[0]
    sar[0] = low[0]

    for i in range(1, n):
        prev_sar = sar[i - 1]
        if uptrend:
            new_sar = prev_sar + af * (ep - prev_sar)
            new_sar = min(new_sar, low[i - 1], low[i - 2] if i >= 2 else low[i - 1])
            if low[i] < new_sar:
                uptrend = False
                new_sar = ep
                ep = low[i]
                af = af_start
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
        else:
            new_sar = prev_sar + af * (ep - prev_sar)
            new_sar = max(new_sar, high[i - 1], high[i - 2] if i >= 2 else high[i - 1])
            if high[i] > new_sar:
                uptrend = True
                new_sar = ep
                ep = high[i]
                af = af_start
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)
        sar[i] = new_sar

    return pd.Series(sar, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    dpo_window: int = 20,
    di_window: int = 14,
    af_start: float = 0.02,
    af_step: float = 0.02,
    af_max: float = 0.20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    dpo = _dpo(close, dpo_window)
    plus_di, minus_di = _directional_movement(df, di_window)
    sar = _parabolic_sar(df, af_start, af_step, af_max)

    dpo_cross_up = (dpo > 0) & (dpo.shift(1) <= 0)
    di_bullish = plus_di > minus_di
    sar_bullish = close > sar

    entry = dpo_cross_up & di_bullish & sar_bullish
    exit_signal = ~sar_bullish

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_vals = entry.to_numpy()
    exit_vals = exit_signal.to_numpy()

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_vals[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
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
