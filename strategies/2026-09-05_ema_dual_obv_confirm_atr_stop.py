"""Strategy: Dual EMA (20/50) price crossover confirmed by OBV-vs-its-own-EMA
volume filter, with an ATR-based stop-loss.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-078):
Per a Google AI-overview synthesis of TradingView/Facebook (Spider Software
Algo Trading) community material on combining EMA crossovers with On-Balance
Volume: "Price Chart: 20-period EMA (fast) and 50-period EMA (slow).
Volume Indicator: On-Balance Volume (OBV) with a 10-period EMA applied to
the OBV line itself... EMA Crossover: The short-term 20 EMA crosses above
the medium-term 50 EMA... OBV Confirmation: The OBV line must be above its
own 10 EMA (or sloping clearly upward), proving that heavy institutional
volume supports the upward price crossover... Stop Loss: Place a protective
stop-loss... at 1.5x ATR from your entry price." This is distinct from
2026-09-04-027 (OBV-crossing-its-own-EMA is the PRIMARY signal, gated by a
close>SMA(200) filter; no price EMA crossover at all) and 2026-09-04-165
(dual EMA(20/50) crossover confirmed by RSI staying above a threshold, a
momentum-oscillator confirmation, not a volume-flow confirmation). Here the
PRIMARY trigger is the price EMA(20/50) crossover itself, and OBV-vs-its-
own-EMA acts purely as a volume-confirmation GATE (must already be true,
not itself crossing) at the moment of the price crossover, plus an
ATR-based stop-loss exit that neither prior variant used.

Signal logic
------------
- Fast EMA(fast_span) and slow EMA(slow_span) of close.
- OBV (cumulative +/- volume by close direction) and its own
  EMA(obv_ema_span).
- Entry (long): fast EMA crosses above slow EMA AND OBV > OBV's own EMA at
  that bar (volume confirms the crossover).
- Exit: fast EMA crosses back below slow EMA, OR close falls below
  (entry_close - atr_mult * ATR(atr_window) at entry), OR a max_hold_days
  time-stop.
- Flat otherwise.

Interface contract (RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _obv(df: pd.DataFrame) -> pd.Series:
    close = df["close"]
    volume = df["volume"]
    direction = np.sign(close.diff().fillna(0.0))
    return (direction * volume).cumsum()


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prior_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prior_close).abs(), (low - prior_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    fast_span: int = 20,
    slow_span: int = 50,
    obv_ema_span: int = 10,
    atr_window: int = 14,
    atr_mult: float = 1.5,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema_fast = close.ewm(span=fast_span, adjust=False).mean()
    ema_slow = close.ewm(span=slow_span, adjust=False).mean()

    obv = _obv(df)
    obv_ema = obv.ewm(span=obv_ema_span, adjust=False).mean()
    obv_confirms = obv > obv_ema

    atr = _atr(df, atr_window)

    bull_cross = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
    bear_cross = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))

    entry = bull_cross.fillna(False) & obv_confirms.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = np.nan

    close_vals = close.to_numpy()
    entry_vals = entry.to_numpy()
    bear_vals = bear_cross.fillna(False).to_numpy()
    atr_vals = atr.to_numpy()

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            stop_hit = (not np.isnan(stop_level)) and close_vals[i] < stop_level
            if bool(bear_vals[i]) or held >= max_hold_days or stop_hit:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_vals[i]) and not np.isnan(atr_vals[i]):
                in_position = True
                entry_idx = i
                stop_level = close_vals[i] - atr_mult * atr_vals[i]
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
