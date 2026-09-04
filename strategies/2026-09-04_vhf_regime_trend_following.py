"""Strategy: Vertical Horizontal Filter (VHF) regime-gated trend following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-152):
VHF (Adam White) measures trend efficiency: VHF_n = (max(close,n) -
min(close,n)) / sum(|close[i]-close[i-1]| for i in n) -- a high/rising VHF
means price moved efficiently in one net direction (trending), a low VHF
means it churned sideways (ranging). Per trendsandbreakouts.com's
explainer, VHF gives no direction itself -- pair it with a directional
signal, and a rising VHF confirms a breakout has "better structural
support". This strategy: long entry when close crosses above a
medium-term SMA (directional signal) AND VHF is both above a threshold
and rising (regime confirmation that the move is efficient, not noise);
exit when close crosses back below the SMA, VHF falls back below the
threshold (regime breaks down), or a max_hold_days time-stop. First VHF
strategy in this repo -- distinct from ADX (already tested/rejected
several times, similar trend-strength-not-direction concept but a
different formula basis: ADX uses directional movement +DI/-DI, VHF uses
raw close range vs. cumulative absolute path).

Signal logic
------------
- VHF[t] = (rolling_max(close, vhf_window) - rolling_min(close, vhf_window))
  / rolling_sum(|close.diff()|, vhf_window)
- Trend direction: close > SMA(close, sma_window)
- Entry (long): close > SMA (uptrend state) AND VHF > vhf_threshold AND
  VHF > VHF.shift(1) (rising).
- Exit: close crosses below SMA, OR VHF < vhf_threshold, OR max_hold_days
  elapsed.
- Flat otherwise.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _vhf(close: pd.Series, window: int) -> pd.Series:
    numerator = close.rolling(window).max() - close.rolling(window).min()
    denominator = close.diff().abs().rolling(window).sum()
    return numerator / denominator.replace(0.0, pd.NA)


def generate_signals(
    price_df: pd.DataFrame,
    vhf_window: int = 28,
    vhf_threshold: float = 0.35,
    sma_window: int = 50,
    max_hold_days: int = 30,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    vhf = _vhf(close, vhf_window).astype(float)
    sma = close.rolling(sma_window).mean()

    uptrend = close > sma
    entry_raw = (uptrend & (vhf > vhf_threshold) & (vhf > vhf.shift(1))).fillna(False).to_numpy()

    exit_trend_break = close < sma
    exit_regime_break = vhf < vhf_threshold
    exit_raw = (exit_trend_break | exit_regime_break).fillna(True).to_numpy()

    pos_arr = [0] * len(df)
    in_pos = False
    hold_days = 0
    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            if exit_raw[i] or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_raw[i]:
                in_pos = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    vhf_window: int = 28,
    vhf_threshold: float = 0.35,
    sma_window: int = 50,
    max_hold_days: int = 30,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        vhf_window=vhf_window,
        vhf_threshold=vhf_threshold,
        sma_window=sma_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
