"""Strategy: Momentum Pinball (LBR/RSI = RSI-of-ROC) oversold entry, daily-bar adaptation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-XXX):
Per the Momentum Pinball trading system (Linda Raschke / Larry Connors,
"Street Smarts"; see MQL5 article "Momentum Pinball trading strategy",
https://www.mql5.com/en/articles/4148): the "LBR/RSI" oscillator is a
3-period RSI applied to a 1-period Rate of Change (ROC) series, computed on
daily bars. Source's disclosed threshold rule: when the LBR/RSI value of
the last closed daily bar drops below 30 (oversold), a long setup is
signaled; the original system then places an intraday stop order at the
first hourly bar's high the next session and typically holds 1-2 days.
Since this repo's data/loaders.py only provides daily OHLCV (no intraday
bars), this implementation adapts the entry to a simple daily-bar version:
enter long at the next day's close after LBR/RSI crosses below
oversold_threshold (30), exit after a short fixed hold_days (source's own
"typically held for 1 to 2 days" -- generalized here as a tunable
max_hold_days), or on LBR/RSI crossing back above exit_threshold (70) as an
early-exit override. First RSI-of-ROC (a "nested" nonstandard oscillator
construction, "LBR/RSI") strategy in this repo -- distinct from plain
RSI-of-price, ROC-of-price threshold crosses, and Cesar Alvarez's
PercentRank-of-ROC (2026-09-04-121, a percentile-rank transform, not an
RSI transform) already tested.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Both accept keyword-arg tunable parameters per RESEARCH_LOOP.md Step 5.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.fillna(50.0)
    return rsi


def _lbr_rsi(df: pd.DataFrame, roc_period: int = 1, rsi_period: int = 3) -> pd.Series:
    """LBR/RSI: an RSI(rsi_period) applied to an ROC(roc_period) series."""
    close = df["close"]
    roc = close.pct_change(roc_period) * 100.0
    return _rsi(roc, rsi_period)


def generate_signals(
    price_df: pd.DataFrame,
    roc_period: int = 1,
    rsi_period: int = 3,
    oversold_threshold: float = 30.0,
    exit_threshold: float = 70.0,
    max_hold_days: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    lbr_rsi = _lbr_rsi(df, roc_period=roc_period, rsi_period=rsi_period)
    oversold_cross = ((lbr_rsi < oversold_threshold) & (lbr_rsi.shift(1) >= oversold_threshold)).fillna(False)
    exit_cross = (lbr_rsi > exit_threshold).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(oversold_cross.iloc[i]):
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
