"""Strategy: MFI dual-threshold "hold-through-the-middle" state machine
(long-only adaptation).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-091):
Per QuantifiedStrategies.com's "How to Build a Profitable Money Flow Index
Strategy Using Python (Rules, Backtest)"
(https://www.quantifiedstrategies.com/how-to-build-a-profitable-money-flow-index-strategy-using-python/,
visited 2026-09-11), the source's own disclosed `calculate_signals` rule:
"whenever the indicator is below threshold1, position=1; if the MFI is
above threshold2, position=-1; if neither condition is met, the indicator
remains the same as the previous value, meaning that the position is
held." Thresholds used in the source's own analysis: threshold1=40%
(entry), threshold2=75% (exit/flip). This is a genuinely distinct MFI
mechanic vs. every prior repo MFI variant: it's a STATE MACHINE that HOLDS
a position through the entire middle zone (40-75) rather than a
threshold-touch-then-recover trigger (e.g. 2026-09-04-033 MFI oversold
bounce, 2026-09-06-129 MFI MA-cross-from-oversold, 2026-09-09-078 MFI
50-centerline cross, 2026-09-11-076 2-day MFI<10 extreme). Long-only
adaptation here (per SAFETY.md and repo convention: no short positions):
enter/stay long whenever MFI < entry_threshold OR already long and MFI
hasn't yet reached exit_threshold; exit (go flat) once MFI crosses above
exit_threshold, re-enter only on a fresh drop below entry_threshold.

Signal logic
------------
- MFI (Money Flow Index, standard 14-period): typical price = (H+L+C)/3;
  raw money flow = typical price * volume; positive/negative money flow
  bucketed by whether typical price rose/fell vs prior bar; money flow
  ratio = sum(pos MF, mfi_window) / sum(neg MF, mfi_window); MFI = 100 -
  100/(1+ratio).
- State machine (source's own rule, long-only adaptation):
    if MFI < entry_threshold: position = 1 (go/stay long)
    elif MFI > exit_threshold: position = 0 (go/stay flat)
    else: position = previous position (hold whatever we were doing)
- No max_hold_days time-stop (source's rule has none -- position holds
  until the opposite threshold is touched, potentially for a long time).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _mfi(df: pd.DataFrame, window: int) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    raw_mf = typical_price * df["volume"]
    tp_diff = typical_price.diff()
    pos_mf = raw_mf.where(tp_diff > 0, 0.0)
    neg_mf = raw_mf.where(tp_diff < 0, 0.0)
    pos_sum = pos_mf.rolling(window).sum()
    neg_sum = neg_mf.rolling(window).sum()
    money_ratio = pos_sum / neg_sum.replace(0.0, 1e-12)
    mfi = 100 - (100 / (1 + money_ratio))
    return mfi


def generate_signals(
    price_df: pd.DataFrame,
    mfi_window: int = 14,
    entry_threshold: float = 40.0,
    exit_threshold: float = 75.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series (long-only state machine)."""
    df = _prep(price_df)
    mfi = _mfi(df, mfi_window)

    position = pd.Series(0, index=df.index, dtype=int)
    prev_pos = 0
    for i in range(len(df)):
        val = mfi.iloc[i]
        if pd.isna(val):
            position.iloc[i] = prev_pos
            continue
        if val < entry_threshold:
            prev_pos = 1
        elif val > exit_threshold:
            prev_pos = 0
        # else: hold previous state unchanged
        position.iloc[i] = prev_pos
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
