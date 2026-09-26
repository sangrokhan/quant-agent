"""Strategy: TRIX signal-line crossover, gated by a 50/200 EMA trend regime
filter AND an explicit low-realized-volatility regime gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-040):
Direct rescue attempt for near-miss 2026-09-23-031 (TRIX(14) signal-line
crossover + 50/200 EMA bullish regime filter, full-period Sharpe 0.983,
narrowly missed 1.0). That entry's own notes explicitly flagged: "the 0.875
low-vol pass rate suggests an explicit vol-gated version could plausibly
clear Sharpe >= 1.0" -- this strategy bakes that low-vol regime membership
directly into the entry condition (following the same pattern as this
repo's already-accepted 2026-09-03-001 BB-meanrev-QQQ-volregime strategy),
rather than only observing it post-hoc in a grid breakdown. Same TRIX/
signal-line/EMA-regime mechanism and source (Google AI Overview synthesis
of TRIX signal-line-crossover parameter tables) as 2026-09-23-031; the only
change is the added realized-volatility regime gate.

Signal logic
------------
- TRIX(trix_window) triple-smoothed EMA rate-of-change oscillator, with
  signal_window-period EMA signal line (unchanged from 2026-09-23-031).
- 50/200 EMA bullish trend regime filter (unchanged).
- NEW: realized volatility regime filter -- rolling `vol_window`-day
  annualized realized vol (std of daily log returns) compared to its
  trailing `vol_lookback`-day median; only trade when current vol <=
  vol_regime_ratio x that trailing median (low-vol regime).
- Entry: TRIX golden cross (TRIX crosses above signal) AND bullish EMA
  regime AND low-vol regime.
- Exit: TRIX dead cross (TRIX crosses below signal) OR vol regime flips to
  high-vol (risk-off exit, matching the BB-meanrev precedent's own regime-
  flip-exit design).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _trix(close: pd.Series, window: int) -> pd.Series:
    ema1 = close.ewm(span=window, adjust=False).mean()
    ema2 = ema1.ewm(span=window, adjust=False).mean()
    ema3 = ema2.ewm(span=window, adjust=False).mean()
    return ema3.pct_change() * 100


def generate_signals(
    price_df: pd.DataFrame,
    trix_window: int = 14,
    signal_window: int = 9,
    fast_ema: int = 50,
    slow_ema: int = 200,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    trix = _trix(close, trix_window)
    signal = trix.ewm(span=signal_window, adjust=False).mean()

    ema_fast = close.ewm(span=fast_ema, adjust=False).mean()
    ema_slow = close.ewm(span=slow_ema, adjust=False).mean()
    bullish_regime = (close > ema_fast) & (close > ema_slow)

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = (realized_vol <= (vol_median * vol_regime_ratio)).fillna(False)

    golden_cross = (trix > signal) & (trix.shift(1) <= signal.shift(1))
    dead_cross = (trix < signal) & (trix.shift(1) >= signal.shift(1))

    entry = golden_cross & bullish_regime & low_vol_regime
    exit_signal = dead_cross | (~low_vol_regime)

    pos_vals = []
    in_pos = False
    for i in range(len(close)):
        if not in_pos and bool(entry.iloc[i]):
            in_pos = True
        elif in_pos and bool(exit_signal.iloc[i]):
            in_pos = False
        pos_vals.append(1 if in_pos else 0)

    return pd.Series(pos_vals, index=close.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    trix_window: int = 14,
    signal_window: int = 9,
    fast_ema: int = 50,
    slow_ema: int = 200,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        trix_window=trix_window,
        signal_window=signal_window,
        fast_ema=fast_ema,
        slow_ema=slow_ema,
        vol_window=vol_window,
        vol_lookback=vol_lookback,
        vol_regime_ratio=vol_regime_ratio,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = (position.shift(1).fillna(0) * daily_ret).fillna(0.0)
    return strat_ret
