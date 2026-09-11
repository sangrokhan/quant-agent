"""Strategy: Ease of Movement (EMV) fast-line / signal-line crossover.

Hypothesis (knowledge_base id: see strategies_log.jsonl 2026-09-11 entry):
Richard Arms' Ease of Movement measures how easily price moves per unit of
volume: EMV_raw = ((high+low)/2 - (prior_high+prior_low)/2) / (volume / (high-low)).
A "fast" short-window SMA of EMV_raw crossing above a slower "signal"
SMA of EMV_raw signals building upside momentum on light volume (a bullish
crossover analogous to a MACD-style dual-moving-average cross), distinct
from the already-tested plain EMV zero-line cross (2026-09-04-115, accepted
w/ SMA trend filter) and EMV bullish-divergence variant (2026-09-08-093).
Source: Google AI-overview synthesis (TradingSim/Investopedia-sourced),
retrieved via browser_exec fallback after web_search DDGS TLS errors,
2026-09-11 iteration: "enter when the fast EMV line crosses above the
signal moving average"; exit "when fast EMV line crosses below the signal
moving average".

Signal logic
------------
- EMV_raw[t] = ((H[t]+L[t])/2 - (H[t-1]+L[t-1])/2) / (volume[t] / (H[t]-L[t]))
  scaled by a constant (box_scale) to keep magnitudes reasonable.
- fast_emv = SMA(EMV_raw, fast_window)
- signal_emv = SMA(EMV_raw, signal_window)  (signal_window > fast_window)
- Entry (long): fast_emv crosses above signal_emv.
- Exit: fast_emv crosses back below signal_emv, OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _compute_emv_raw(df: pd.DataFrame, box_scale: float = 1_000_000.0) -> pd.Series:
    high = df["high"]
    low = df["low"]
    volume = df["volume"].replace(0, pd.NA)

    mid = (high + low) / 2.0
    mid_prev = mid.shift(1)
    distance_moved = mid - mid_prev

    hl_range = (high - low).replace(0, pd.NA)
    box_ratio = (volume / box_scale) / hl_range

    emv_raw = (distance_moved / box_ratio).astype(float)
    return emv_raw.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 7,
    signal_window: int = 14,
    box_scale: float = 1_000_000.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    emv_raw = _compute_emv_raw(df, box_scale=box_scale)

    fast_emv = emv_raw.rolling(fast_window).mean()
    signal_emv = emv_raw.rolling(signal_window).mean()

    bullish_cross = (fast_emv > signal_emv) & (fast_emv.shift(1) <= signal_emv.shift(1))
    bearish_cross = (fast_emv < signal_emv) & (fast_emv.shift(1) >= signal_emv.shift(1))

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(df)):
        if in_position:
            held = i - entry_idx
            if bool(bearish_cross.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(bullish_cross.iloc[i]):
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
