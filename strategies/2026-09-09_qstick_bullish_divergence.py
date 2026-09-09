"""Strategy: Qstick (Tushar Chande) bullish price/indicator divergence.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-088):
Per https://www.tradingpedia.com/forex-trading-indicators/chandes-quick-stick-qstick/
(accessed via browser_exec fallback -- web_search's DDGS backend errored with
a TLS connection error), Chande documents three distinct Qstick signal
families: (1) zero-line crossover, (2) extreme-level reversal, (3)
divergence -- "If the market is forming lower lows while the Qstick is
forming higher lows, this represents a bullish divergence and is a signal
to buy." This repo has already tested zero-line-crossover variants three
times (2026-09-04-136 SMA-of-own-SMA, 2026-09-06-105 EMA-vs-signal-line,
2026-09-09-077 ADX-gated) but never the divergence family, which is a
materially different (price-vs-oscillator swing comparison) condition.

Qstick itself: SMA (or EMA) of (close - open) over `qstick_window` --
a smoothed measure of whether recent candle bodies have closed above (bull)
or below (bear) their opens.

Signal logic
------------
- price makes a new `swing_lookback`-bar low (close <= rolling min close)
  while Qstick is ABOVE the Qstick value recorded at the prior new-low bar
  within that window (Qstick "higher low" vs price "lower low") -- the
  divergence condition itself.
- Entry trigger (needed since divergence alone is a static condition, not a
  timing signal): Qstick crosses back above zero (source's own
  zero-line-crossover trigger, reused here as the confirmation that
  bullish momentum has actually resumed after the divergence was flagged).
- Exit: Qstick crosses back below zero, or a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _qstick(df: pd.DataFrame, qstick_window: int) -> pd.Series:
    body = df["close"] - df["open"]
    return body.rolling(qstick_window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    qstick_window: int = 14,
    swing_lookback: int = 20,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Bullish divergence: today's price makes a `swing_lookback`-day low
    (close <= rolling min close) while Qstick is ABOVE its own value at the
    prior new-low bar within the window (Qstick higher low vs price lower
    low). Entry fires when that divergence condition held recently (within
    the lookback window) AND Qstick crosses back above zero (confirmation
    trigger per source's zero-line-crossover rule).
    Exit: Qstick crosses back below zero, or a max_hold_days time-stop.
    """
    df = _prep(price_df)
    close = df["close"]
    qstick = _qstick(df, qstick_window)

    rolling_min_close = close.rolling(swing_lookback).min()
    is_price_low = close <= rolling_min_close

    # Value of Qstick at the first bar of the current lookback window
    # (approximation of the "prior swing low" reference point).
    prior_low_qstick = qstick.rolling(swing_lookback).apply(
        lambda window: window.iloc[0] if len(window) else float("nan"), raw=False
    )

    bullish_divergence = is_price_low & (qstick > prior_low_qstick)
    # Divergence condition must have been flagged recently (within the same
    # lookback window) for the zero-cross confirmation to count as acting on
    # it, rather than requiring the exact same bar.
    divergence_recent = bullish_divergence.fillna(False).rolling(swing_lookback, min_periods=1).max().astype(bool)

    qstick_cross_up = (qstick > 0) & (qstick.shift(1) <= 0)
    qstick_cross_down = (qstick < 0) & (qstick.shift(1) >= 0)

    entry = divergence_recent & qstick_cross_up.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    n = len(close)
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(qstick_cross_down.iloc[i]) or held >= max_hold_days:
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
