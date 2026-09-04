"""Strategy: Stochastic Momentum Index (SMI) oversold-crossover mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-140):
The Stochastic Momentum Index (William Blau, a smoothed refinement of the
classic Stochastic %K that measures close relative to the midpoint of the
recent high/low range rather than the range's low end) tends to reach
extreme oversold/overbought zones before turning. Per Google's AI-overview
synthesis of TradingView/QuantifiedStrategies explainers, the canonical
systematic long entry is: SMI crosses above its own signal line (EMA of
SMI) while/after SMI was below an oversold threshold (typically -40); exit
when SMI crosses back below the signal line, or reaches the opposite
overbought extreme (+40), or a max-hold time-stop backstop. First
Stochastic-Momentum-Index (distinct from the already-tested classic
Stochastic %K/%D and StochRSI) strategy tried in this repo.

Signal logic
------------
- SMI (Blau) construction over `smi_window`:
    mid = (highest_high + lowest_low) / 2  (over smi_window)
    diff = close - mid
    hl_range = highest_high - lowest_low
    double-smoothed diff and hl_range with EMA(smooth1) then EMA(smooth2)
    SMI = 100 * smoothed_diff / (0.5 * smoothed_range)
- signal_line = EMA(SMI, signal_window)
- Entry (long): SMI crosses above signal_line AND SMI was below
  `oversold_threshold` within the last `lookback_confirm` bars (confirms the
  crossover happens coming OUT of an oversold extreme, not mid-range noise).
- Exit: SMI crosses below signal_line, OR SMI reaches
  `overbought_threshold` (take profit at opposite extreme), OR a
  max_hold_days time-stop backstop.
- Flat otherwise (long-only; no short leg per SAFETY.md scope).

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


def _smi(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    smi_window: int,
    smooth1: int,
    smooth2: int,
) -> pd.Series:
    highest_high = high.rolling(smi_window).max()
    lowest_low = low.rolling(smi_window).min()
    mid = (highest_high + lowest_low) / 2.0
    diff = close - mid
    hl_range = highest_high - lowest_low

    smoothed_diff = diff.ewm(span=smooth1, adjust=False).mean().ewm(span=smooth2, adjust=False).mean()
    smoothed_range = hl_range.ewm(span=smooth1, adjust=False).mean().ewm(span=smooth2, adjust=False).mean()

    smi = 100.0 * smoothed_diff / (0.5 * smoothed_range.replace(0, pd.NA))
    return smi.astype(float)


def generate_signals(
    price_df: pd.DataFrame,
    smi_window: int = 13,
    smooth1: int = 25,
    smooth2: int = 2,
    signal_window: int = 9,
    oversold_threshold: float = -40.0,
    overbought_threshold: float = 40.0,
    lookback_confirm: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    smi = _smi(high, low, close, smi_window, smooth1, smooth2)
    signal_line = smi.ewm(span=signal_window, adjust=False).mean()

    was_oversold = (smi < oversold_threshold).rolling(lookback_confirm, min_periods=1).max().astype(bool)
    cross_up = (smi > signal_line) & (smi.shift(1) <= signal_line.shift(1))
    cross_down = (smi < signal_line) & (smi.shift(1) >= signal_line.shift(1))

    entry = cross_up & was_oversold.fillna(False)
    exit_signal = cross_down | (smi >= overbought_threshold)

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
