"""Strategy: IBS extreme-threshold trend-reversal with previous-day input.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-071):
Per https://medium.com/@redsword_23261/internal-bar-strength-trend-reversal-
trading-system-c5f8c7e5362e, "Internal Bar Strength Trend Reversal Trading
System" uses IBS computed from the PREVIOUS day's bar (not the same-day
close), with EXTREME asymmetric thresholds far outside this repo's typical
0.2/0.8 IBS-entries range: source's own recommended defaults are entry
threshold 0.09 (QQQ) / 0.11 (SPY), exit threshold 0.985 (QQQ) / 0.995
(SPY), trend filter EMA(220) (QQQ) / EMA(200) (SPY), max holding period 14
days. This repo has 38+ prior IBS entries but all use same-day IBS with
0.2-0.3 entry / 0.5-0.8 exit thresholds -- none tests this specific
previous-day-input + extreme-threshold + EMA-filter combination from the
source's own disclosed defaults.

Signal logic
------------
- IBS[t] = (Close[t-1] - Low[t-1]) / (High[t-1] - Low[t-1]) -- uses
  YESTERDAY's bar, evaluated as of today's decision point (avoids
  same-bar lookahead by construction, decision made using fully-closed
  prior bar).
- Entry (long): IBS < entry_threshold (extreme oversold, prior bar closed
  very near its own low) AND close > EMA(trend_window) (established
  uptrend).
- Exit: IBS >= exit_threshold (extreme overbought reversion target,
  prior bar closed very near its own high), OR a max_hold_days time-stop.
- Flat otherwise. Pyramiding/pullback-distance features from the source
  are simplified out (single-entry-at-a-time, matching this repo's
  {0,1} position contract).

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


def generate_signals(
    price_df: pd.DataFrame,
    entry_threshold: float = 0.09,
    exit_threshold: float = 0.985,
    trend_window: int = 220,
    max_hold_days: int = 14,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    rng = (high - low).replace(0.0, 1e-12)
    ibs = (close - low) / rng
    ibs_prev_bar = ibs.shift(1)  # yesterday's IBS, available at today's decision point

    ema_trend = close.ewm(span=trend_window, adjust=False).mean()

    entry = (ibs_prev_bar < entry_threshold) & (close > ema_trend)
    exit_signal = ibs_prev_bar >= exit_threshold

    entry = entry.fillna(False)
    exit_signal = exit_signal.fillna(False)

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
