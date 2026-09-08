"""Strategy: Pring's Know Sure Thing (KST) oscillator, signal-line crossover
from negative territory.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-XXX):
Per gocharting.com's KST docs (read in-browser 2026-09-08, web_extract
backend unavailable -- DuckDuckGo search-only, fell back to browser_exec),
the Know Sure Thing oscillator is a smoothed, weighted sum of four
rate-of-change readings designed to catch MAJOR trend changes. The source's
own explicit strategy rule: "Apply KST to weekly charts. Enter long when KST
crosses above its signal line after being in negative territory. Exit when
KST crosses back below its signal line. The longer the prior downtrend, the
more powerful the subsequent signal." It also explicitly warns KST is
unsuited to short-term/daily use and works best on broad indices.

This is the FIRST Pring KST strategy in this repo (0 prior hits on "KST" /
"Know Sure Thing" / "Pring KST" in strategies_index.jsonl as of this
iteration). Since our data is daily bars (not weekly), we approximate the
source's weekly-chart intent with a `scale` multiplier applied to Pring's
standard ROC/SMA periods (scale=5 roughly maps daily bars to weekly-lookback
equivalents; scale=1 tests the raw daily-period version as a baseline/
robustness contrast) -- this scale factor is the primary grid-tested
parameter, directly probing the source's own "don't use short-term" caveat.

Signal logic
------------
- KST = 1*SMA(ROC(close, 10*scale), 10*scale)
      + 2*SMA(ROC(close, 15*scale), 10*scale)
      + 3*SMA(ROC(close, 20*scale), 10*scale)
      + 4*SMA(ROC(close, 30*scale), 15*scale)
  (ROC in percent; standard Pring weights 1/2/3/4)
- Signal line = SMA(KST, signal_window)
- Entry (long): KST crosses above its signal line, AND KST was in negative
  territory (< 0) at some point within `lookback_neg` bars prior to the
  cross (source's own "after being in negative territory" qualifier).
- Exit: KST crosses back below its signal line, OR a max_hold_days time-stop
  (source doesn't specify a stop; added for risk control per repo
  convention).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _roc(close: pd.Series, period: int) -> pd.Series:
    return (close / close.shift(period) - 1.0) * 100.0


def _kst(close: pd.Series, scale: int) -> pd.Series:
    r1 = _roc(close, 10 * scale).rolling(10 * scale).mean()
    r2 = _roc(close, 15 * scale).rolling(10 * scale).mean()
    r3 = _roc(close, 20 * scale).rolling(10 * scale).mean()
    r4 = _roc(close, 30 * scale).rolling(15 * scale).mean()
    return 1 * r1 + 2 * r2 + 3 * r3 + 4 * r4


def generate_signals(
    price_df: pd.DataFrame,
    scale: int = 5,
    signal_window: int = 9,
    lookback_neg: int = 20,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    kst = _kst(close, scale)
    signal = kst.rolling(signal_window).mean()

    cross_up = (kst > signal) & (kst.shift(1) <= signal.shift(1))
    cross_down = (kst < signal) & (kst.shift(1) >= signal.shift(1))

    was_negative = (kst.shift(1) < 0).rolling(lookback_neg, min_periods=1).max().astype(bool)
    entry_signal = cross_up & was_negative

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    for i in range(len(close)):
        if not in_pos:
            if bool(entry_signal.iloc[i]):
                in_pos = True
                entry_idx = i
                position.iloc[i] = 1
        else:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    scale: int = 5,
    signal_window: int = 9,
    lookback_neg: int = 20,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no txn costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        scale=scale,
        signal_window=signal_window,
        lookback_neg=lookback_neg,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change()
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)
