"""Strategy: Williams Fractal breakout (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's
id): per Bill Williams' Fractal indicator (Google AI-overview / TradingView
/ LiteFinance / Quantified Strategies synthesis), a "Fractal high" is a
5-bar pattern where the center bar's high is strictly greater than the
high of the 2 bars on either side (a confirmed local top, lagging by 2
bars for confirmation); a "Fractal low" is the mirror pattern for lows.
Per LiteFinance's own breakout rule: "at the moment of the breakout of the
fractal level, open a long position ... and set a stop loss below the
corrective fractal" -- i.e. a decisive close above the most recently
confirmed Fractal HIGH triggers a long entry (breakout continuation, not
reversal), with a stop below the most recently confirmed Fractal LOW.
Exit: close falls back below the stop-loss fractal low, OR a max_hold_days
time-stop (per Quantified Strategies' own N-day fixed-hold variant, which
the source notes as one of its own tested exit rules).

Sources read this iteration:
- Google search results snippet synthesis + LiteFinance/Quantified
  Strategies/TradingView Williams Fractal breakout numeric rules (direct
  LiteFinance article URL 404'd on fetch -- rules taken from the visible
  Google SERP snippet text, which was itself specific and numeric enough
  to implement directly).

First Williams Fractal strategy in this knowledge base (zero prior
matches).

Signal logic
------------
- Fractal high at bar i (confirmed 2 bars later, at i+2): high[i] is the
  max of high[i-2:i+3] (5-bar window, strict local max at center).
- Fractal low at bar i (confirmed 2 bars later): low[i] is the min of
  low[i-2:i+3].
- Track most recently confirmed fractal high level and fractal low level.
- Long entry: close decisively breaks above the most recently confirmed
  fractal high level (close > fractal_high_level).
- Stop-loss: most recently confirmed fractal low level (at time of entry).
- Exit: close < stop-loss level, OR max_hold_days time-stop.
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


def generate_signals(
    price_df: pd.DataFrame,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    n = len(df.index)

    # Confirmed fractal high/low at bar i (using bars i-2..i+2), available
    # from bar i+2 onward (2-bar confirmation lag, standard for Williams
    # Fractals).
    fractal_high_at = pd.Series(index=df.index, dtype=float)
    fractal_low_at = pd.Series(index=df.index, dtype=float)
    for i in range(2, n - 2):
        window_high = high.iloc[i - 2 : i + 3]
        window_low = low.iloc[i - 2 : i + 3]
        if high.iloc[i] == window_high.max() and (window_high == window_high.max()).sum() == 1:
            fractal_high_at.iloc[i] = high.iloc[i]
        if low.iloc[i] == window_low.min() and (window_low == window_low.min()).sum() == 1:
            fractal_low_at.iloc[i] = low.iloc[i]

    position = pd.Series(0, index=df.index, dtype=int)

    last_fractal_high = None
    last_fractal_low = None
    in_position = False
    hold_days = 0
    stop_price = None

    for i in range(n):
        # A fractal confirmed AT bar i-2 becomes known/usable starting bar i
        # (2-bar lag baked into fractal_high_at/_low_at already being
        # indexed at the CENTER bar -- so it's "known" once we're 2 bars
        # past it; since we already only fill it for i in [2, n-3], we
        # additionally require the confirming bar (i+2) to have occurred).
        confirm_idx = i - 2
        if confirm_idx >= 0:
            if not pd.isna(fractal_high_at.iloc[confirm_idx]):
                last_fractal_high = fractal_high_at.iloc[confirm_idx]
            if not pd.isna(fractal_low_at.iloc[confirm_idx]):
                last_fractal_low = fractal_low_at.iloc[confirm_idx]

        c = close.iloc[i]

        if in_position:
            hold_days += 1
            if c < stop_price or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                stop_price = None
            else:
                position.iloc[i] = 1
                continue

        if last_fractal_high is not None and c > last_fractal_high and last_fractal_low is not None:
            in_position = True
            hold_days = 1
            stop_price = last_fractal_low
            position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(price_df, max_hold_days=max_hold_days)
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
