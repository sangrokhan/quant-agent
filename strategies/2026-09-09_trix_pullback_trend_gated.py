"""Strategy: TRIX pullback-in-trend entry, trend-baseline gated (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-067):
Per https://trendsandbreakouts.com/trix ("TRIX Strategy - Pullback and
Crossover Trading Rules", browser_exec fallback -- web_search DDGS errored/
returned no results for several direct queries), the source's own disclosed
trading rule is explicitly NOT a standalone signal-line crossover: "A
practical long setup starts with trend context. Price should be above a
rising baseline, such as a medium-term moving average... Then wait for a
pullback while TRIX softens. The entry comes when TRIX turns up again or
crosses above its signal line while price stabilizes near support." The
source explicitly warns that "treating every signal-line crossover as a
trade" in choppy conditions "leads to whipsaws" -- a trend-baseline gate
plus a genuine pullback precondition (TRIX must have recently softened/
dipped, not just be crossing up from a flat or already-rising state) is the
key differentiator from this repo's existing unconditional TRIX signal-cross
strategy (2026-09-04-038, zero-line filter only, no trend baseline or
pullback precondition) and the TRIX bullish-divergence strategy
(2026-09-07-018, divergence pattern trigger, no baseline/pullback
mechanism). This strategy implements the source's own 3-part rule stack:
(1) price above a rising baseline SMA, (2) TRIX must have declined over the
preceding pullback window (the "softening" precondition), (3) TRIX crosses
back above its signal line as the actual entry trigger.

TRIX formula (standard):
    EMA1 = EMA(close, trix_window)
    EMA2 = EMA(EMA1, trix_window)
    EMA3 = EMA(EMA2, trix_window)
    TRIX = 100 * (EMA3 / EMA3.shift(1) - 1)
    Signal = EMA(TRIX, signal_window)

Signal logic
------------
- Trend gate: close > baseline SMA(baseline_window) AND baseline is rising
  (baseline > baseline.shift(baseline_slope_lookback)).
- Pullback precondition ("TRIX softens"): TRIX one bar ago is lower than it
  was `pullback_window` bars before that (i.e. TRIX has net declined over
  the pullback window leading up to today), signaling a genuine dip rather
  than an already-accelerating TRIX.
- Entry (long): TRIX crosses above signal (fresh cross) AND trend gate AND
  pullback precondition, all on the same bar.
- Exit: TRIX crosses back below signal, OR close drops below the baseline
  (trend-structure break, per source's own emphasis on price structure for
  stops/exits), OR a `max_hold_days` time-stop (source doesn't specify a
  hard time exit; this repo consistently adds one as a safety net).
- Flat otherwise; long-only, no shorting (per repo convention).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly across a parameter grid).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _trix(close: pd.Series, window: int) -> pd.Series:
    ema1 = close.ewm(span=window, adjust=False).mean()
    ema2 = ema1.ewm(span=window, adjust=False).mean()
    ema3 = ema2.ewm(span=window, adjust=False).mean()
    trix = 100.0 * (ema3 / ema3.shift(1) - 1.0)
    return trix


def generate_signals(
    price_df: pd.DataFrame,
    trix_window: int = 15,
    signal_window: int = 9,
    baseline_window: int = 50,
    baseline_slope_lookback: int = 5,
    pullback_window: int = 8,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    trix = _trix(close, trix_window)
    signal = trix.ewm(span=signal_window, adjust=False).mean()

    baseline = close.rolling(baseline_window).mean()
    baseline_rising = baseline > baseline.shift(baseline_slope_lookback)
    trend_gate = (close > baseline) & baseline_rising.fillna(False)

    # "TRIX softened" precondition: net decline over the pullback window
    # leading up to yesterday's bar (avoid look-ahead: compare shift(1) to
    # shift(1 + pullback_window)).
    softened = trix.shift(1) < trix.shift(1 + pullback_window)

    cross_up = (trix > signal) & (trix.shift(1) <= signal.shift(1))
    cross_down = (trix < signal) & (trix.shift(1) >= signal.shift(1))

    entry = cross_up & trend_gate.fillna(False) & softened.fillna(False)
    exit_cross = cross_down
    exit_trend_break = close < baseline

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
