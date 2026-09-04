"""Strategy: Pring's Special K (simplified multi-ROC composite momentum)
crossing its own smoothed moving average.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-009):
Martin Pring's Special K is a composite momentum oscillator combining
smoothed rate-of-change (ROC) indicators across short/medium/long lookback
periods into a single curve, meant to reflect market strength across
multiple timeframes at once. Per technicalresources.in's "Special K +
Moving Average Crossover" strategy, the mechanical rule is: plot a smoothed
moving average of Special K itself (13-EMA or 21-SMA), and trade the
crossover -- long when Special K crosses above its own moving average,
exit/short when it crosses below. This is implemented here as a simplified
Special K (weighted sum of 6 ROC-then-SMA-smoothed components at periods
10/15/20/30/40/65, following the article's summary formula list) rather
than Pring's full original 10-component formula, since the exact original
weights/smoothing windows are proprietary to Pring's own charting
software. First Special K strategy in this repo -- distinct from the
already-tested Know Sure Thing (KST, 2026-09-04-057, also Pring, but a
fixed 4-ROC weighted sum traded via a fixed 9-period-SMA zero-region
signal-line cross, not a tunable MA-crossover).

Signal logic
------------
- For each (roc_period, sma_period) pair in {(10,10), (15,10), (20,10),
  (30,15), (40,50), (65,65)}: compute ROC(close, roc_period), then
  SMA(that ROC, sma_period).
- Special K = simple sum of all 6 smoothed-ROC components (equal weighting;
  Pring's original uses unequal weights not fully disclosed by the free
  source).
- signal_line = EMA(Special K, sk_signal_span) (default 13, per the
  source's own "13-period EMA" example).
- Entry (long): Special K crosses above signal_line.
- Exit: Special K crosses below signal_line, OR a max_hold_days time-stop
  backstop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd

_ROC_SMA_PAIRS = [(10, 10), (15, 10), (20, 10), (30, 15), (40, 50), (65, 65)]


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _special_k(close: pd.Series) -> pd.Series:
    total = pd.Series(0.0, index=close.index)
    for roc_period, sma_period in _ROC_SMA_PAIRS:
        roc = 100.0 * (close / close.shift(roc_period) - 1.0)
        smoothed = roc.rolling(sma_period, min_periods=max(2, sma_period // 2)).mean()
        total = total.add(smoothed, fill_value=0.0)
    return total


def generate_signals(
    price_df: pd.DataFrame,
    sk_signal_span: int = 13,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    special_k = _special_k(close)
    signal_line = special_k.ewm(span=sk_signal_span, adjust=False).mean()

    above = special_k > signal_line
    entry = above & (~above.shift(1).fillna(False))
    exit_signal = ~above

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
    daily_ret = position.shift(1).fillna(0) * close.pct_change().fillna(0.0)
    return daily_ret
