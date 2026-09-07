"""Strategy: ATR 2x-expansion + 20-day-high breakout + volume confirmation
("ATR Volatility Expansion" swing strategy).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-061):
Per swingfolio.com's "Mastering the ATR Volatility Expansion Trading
Strategy" article, long entry requires THREE conditions simultaneously:
(1) current ATR(atr_window) expands to >= atr_expansion_mult (default 2.0x)
    its own rolling atr_ma_window average -- a much stronger threshold than
    prior ATR-expansion tests in this repo (2026-09-05-055 used a generic
    "surge above its rolling average", no fixed multiplier);
(2) close breaks above the rolling breakout_window-day high (source: "Price
    Breaks a 20-Day High" -- confirms the expansion is directional, not
    just noise);
(3) volume confirmation: current volume >= vol_mult (default 1.5x) its
    rolling vol_window-day average volume (source: "Volume Confirmation" --
    NOT present in any prior ATR-expansion/breakout strategy in this repo).

Exit is a dual rule, distinct from 2026-09-05-055's mean-reversion-to-basis
exit: (a) "Volatility Contraction Exit" -- ATR slopes back down to/below its
own rolling average (the explosive phase is over), OR (b) an ATR-based
stop-loss at stop_atr_mult (default 1.5x) times the ATR value recorded AT
ENTRY, below the entry close (source's explicit stop-loss rule) -- a fixed
per-trade stop rather than a chandelier/trailing stop, distinct from
2026-09-04-025's chandelier ATR trailing stop. A max_hold_days safety cap
is added since the source only describes exits qualitatively.

First strategy in this repo combining ALL THREE of {ATR-magnitude-expansion
gate, price breakout, volume confirmation} together with a volatility-
contraction-based exit + fixed ATR stop -- distinct from every prior
Keltner/ATR/Donchian/volume-confirmed-breakout combination already tested
(2026-09-03-016 plain Keltner breakout has no ATR-expansion or volume gate;
2026-09-05-055 ATR-expansion has no volume gate and uses a basis-crossing
exit not a contraction-based exit; 2026-09-05-078/2026-09-06-091/094/095/125
volume-confirmed breakouts use Donchian/other bands, not an explicit ATR
multiple-of-its-own-average gate).

Source: https://swingfolio.com/blog/atr-volatility-expansion-trading-strategy

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 14,
    atr_ma_window: int = 20,
    atr_expansion_mult: float = 2.0,
    breakout_window: int = 20,
    vol_window: int = 20,
    vol_mult: float = 1.5,
    stop_atr_mult: float = 1.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    atr = _atr(df, atr_window)
    atr_ma = atr.rolling(atr_ma_window).mean()
    atr_expanded = atr >= (atr_ma * atr_expansion_mult)

    rolling_high = close.shift(1).rolling(breakout_window).max()
    price_breakout = close > rolling_high

    if "volume" in df.columns:
        volume = df["volume"]
        vol_ma = volume.rolling(vol_window).mean()
        vol_confirmed = volume >= (vol_ma * vol_mult)
    else:
        vol_confirmed = pd.Series(True, index=close.index)

    entry = (atr_expanded & price_breakout & vol_confirmed).fillna(False)
    vol_contraction_exit = (atr <= atr_ma).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = 0.0
    stop_price = 0.0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            px = close.iloc[i]
            hit_stop = px <= stop_price
            hit_contraction = bool(vol_contraction_exit.iloc[i])
            hit_time = held >= max_hold_days
            if hit_stop or hit_contraction or hit_time:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                entry_price = close.iloc[i]
                atr_at_entry = atr.iloc[i]
                if pd.isna(atr_at_entry):
                    atr_at_entry = 0.0
                stop_price = entry_price - stop_atr_mult * atr_at_entry
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
