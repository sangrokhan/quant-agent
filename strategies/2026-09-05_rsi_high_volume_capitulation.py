"""Strategy: RSI(14) oversold confirmed by ABOVE-average (heavy capitulation)
volume, long-only. A distinct high-volume-confirmation mean-reversion
variant, targeted at crypto majors.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-083):
Per TradingView's "RSI Volume Ladder" strategy (wielkieef, via Google
search snippet): "A long-only pyramiding strategy that scales into
corrections using RSI oversold conditions confirmed by above-average
volume... developed on crypto majors (BTC, ETH)." The core, non-pyramiding
signal logic is: RSI(14) crosses below an oversold threshold (30) AND that
day's volume exceeds its own rolling average by a confirmation ratio
(heavy-volume capitulation, not a quiet drift down) -- go long on the
subsequent RSI recovery back above the threshold. This is the OPPOSITE
volume-confirmation logic from this repo's already-tested Connors RSI +
volume-EXHAUSTION variant (2026-09-05-042, which required LOW volume as a
"quiet capitulation" signal); here HIGH volume at the oversold dip is the
confirming signal (heavy panic-selling exhaustion, the more common
retail-trading-education interpretation), and the target asset class is
explicitly crypto majors per the source, unlike most of this repo's
RSI-oversold variants which were built/tuned for equities first.

Signal logic
------------
- RSI(rsi_window) standard Wilder RSI of close.
- Volume confirmation: today's volume >= vol_ma_window-day average volume *
  vol_confirm_ratio (heavy-volume capitulation dip).
- Entry (long): RSI crosses below oversold_level (30) WITH volume
  confirmation flagged within confirm_recency bars, THEN RSI crosses back
  above oversold_level (recovery trigger).
- Exit: RSI crosses above exit_level (60, momentum fading), or a
  max_hold_days time-stop.
- Flat otherwise. (Non-pyramiding simplification of the source's scaling
  approach, consistent with this repo's single-position convention.)

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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    oversold_level: float = 30.0,
    exit_level: float = 60.0,
    vol_ma_window: int = 20,
    vol_confirm_ratio: float = 1.5,
    confirm_recency: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    rsi = _rsi(close, rsi_window)
    vol_ma = volume.rolling(vol_ma_window).mean()
    high_volume = volume >= (vol_ma * vol_confirm_ratio)

    oversold_dip = (rsi < oversold_level) & high_volume
    dip_recent = oversold_dip.rolling(confirm_recency, min_periods=1).max().astype(bool)

    rsi_recover = (rsi > oversold_level) & (rsi.shift(1) <= oversold_level)
    entry = dip_recent.fillna(False) & rsi_recover.fillna(False)

    exit_cross = (rsi > exit_level) & (rsi.shift(1) <= exit_level)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    entry_vals = entry.to_numpy()
    exit_vals = exit_cross.fillna(False).to_numpy()

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
