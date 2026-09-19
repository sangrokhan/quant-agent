"""Strategy: MACD-Histogram trough-entry, first-up-day exit (mean reversion).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per QuantifiedStrategies.com's "MACD Histogram Trading Strategy" article
(https://www.quantifiedstrategies.com/macd-histogram/, read via browser_exec
fallback), a standard MACD(12,26,9) histogram that is BELOW the zero line
but has just turned from falling to rising (a "trough" / local bottom in
momentum while still bearish) marks a short-term bullish mean-reversion
entry. The disclosed exit rule is asymmetric and NOT signal-based: exit on
the very first day the close is higher than the prior day's close (a
"first up day" exit), not on any indicator re-cross or fixed holding
period. Source's own backtest (77-ETF sample + QLD 2007-present) reports
long-only outperforming short-only decisively, so this implementation is
long-only.

This is architecturally distinct from every other MACD-histogram entry
already in this repo:
  - 2026-09-08-085: bullish DIVERGENCE (price lower-low vs histogram
    higher-low) trigger, signal-based exit.
  - 2026-09-18-059: histogram used as a binary momentum-confirmation GATE
    on a triple-MA ribbon crossover, not a trough-timing trigger itself.
  - 2026-09-14-133: Elder Impulse continuous SIZING dial, not a discrete
    entry/exit rule.
None of those use this trough-below-zero ENTRY + first-higher-close EXIT
asymmetric construction.

Signal logic
------------
- Standard MACD(12,26,9): macd_line = EMA(close,12) - EMA(close,26);
  signal_line = EMA(macd_line,9); histogram = macd_line - signal_line.
- Entry (long): histogram(t-1) < 0 AND histogram(t) < 0 AND
  histogram(t) > histogram(t-1) (i.e. histogram is below zero and just
  turned upward -- a "trough" while still bearish) -- entered at that
  day's close.
- Exit: the first day close(t) > close(t-1) (first up day) while in a
  position -- exited at that day's close. If never triggered, an optional
  max_hold_days safety cap prevents indefinite single-name holds (source
  article doesn't mention one explicitly but this repo's other strategies
  consistently use a cap as a risk-control convention; kept generous by
  default so it rarely binds).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1} position series
    generate_returns(price_df, **params) -> pd.Series daily strategy returns
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
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line

    hist_prev = hist.shift(1)
    entry = (hist_prev < 0) & (hist < 0) & (hist > hist_prev)

    close_prev = close.shift(1)
    exit_up_day = close > close_prev

    entry = entry.fillna(False)
    exit_up_day = exit_up_day.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_up_day.iloc[i]) or held >= max_hold_days:
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
