"""Strategy: Statistical Dislocation Mean Reversion (quantile-based drop + uptrend filter).

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per Quantitativo's "A Mean Reversion Strategy from First Principles Thinking"
(https://www.quantitativo.com/p/a-mean-reversion-strate...) and its follow-up
improvement article "Murphy's Law" (https://www.quantitativo.com/p/murphys-law):
a stock's own trailing N-day return distribution defines what counts as a
"statistically unlikely" drop for THAT stock (not a fixed pct threshold
shared across all names) -- when an `n_day_return` percentile-ranks below
`quantile_threshold` of its own trailing `lookback_years`-equivalent (here,
a rolling `dist_window`-day) distribution, AND the stock remains in a
longer-term uptrend (close > SMA(`trend_window`), a "non-fundamental
dislocation, not a fundamentally-driven repricing" proxy per the source's
own diagnosis of what breaks the strategy), the drop tends to mean-revert;
hold for a fixed `hold_days`. Distinct from every other quantile-gated
construction in this repo (2026-09-05-020 uses Bollinger Bandwidth's own
percentile rank as a volatility-squeeze gate, unrelated indicator; 2026-09-
08-049 uses DPO's percentile rank as a cycle-timing gate) -- this is the
first strategy to percentile-rank the RAW RETURN itself against its own
rolling historical distribution as the entry trigger, rather than
percentile-ranking a derived indicator.

Signal logic
------------
- n_day_return[t] = close[t] / close[t-n_day_window] - 1.
- rolling_quantile[t] = the `quantile_threshold` quantile of n_day_return
  over the trailing `dist_window` days (as of t, using only data known by
  t's close).
- drop_signal[t] = n_day_return[t] <= rolling_quantile[t] (today's N-day
  return is unusually low vs its own recent distribution).
- trend_filter[t] = close[t] > SMA(trend_window)[t].
- Entry: drop_signal[t-1] AND trend_filter[t-1] (decision known as of prior
  close, shifted forward 1 bar) -> hold long for `hold_days` trading days
  (fixed-duration exit, per the source's own "closed once it reverts" ~
  simplified here to a fixed-hold as in the source's own baseline
  measurement methodology).
- No overlapping-position logic needed for a single-symbol backtest: while
  in the position (fixed hold_days countdown), new entry signals are
  ignored until the position closes.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
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
    n_day_window: int = 3,
    dist_window: int = 252,
    quantile_threshold: float = 0.15,
    trend_window: int = 200,
    hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} series: 1 = holding a fixed-duration long position."""
    df = _prep(price_df)
    close = df["close"]

    n_day_return = close.pct_change(n_day_window)
    rolling_quantile = n_day_return.rolling(dist_window, min_periods=max(30, dist_window // 4)).quantile(
        quantile_threshold
    )
    drop_signal = n_day_return <= rolling_quantile

    sma = close.rolling(trend_window).mean()
    trend_filter = close > sma

    entry_trigger = (drop_signal & trend_filter).shift(1).fillna(False)

    # Fixed-duration hold, non-overlapping: once triggered, stay in position
    # for hold_days bars, ignoring new entry signals until it closes.
    position = pd.Series(0, index=df.index, dtype=int)
    countdown = 0
    for i in range(len(df)):
        if countdown > 0:
            position.iloc[i] = 1
            countdown -= 1
        elif entry_trigger.iloc[i]:
            position.iloc[i] = 1
            countdown = hold_days - 1
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Close-to-close returns while holding the fixed-duration dislocation trade."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(price_df, **kwargs)
    asset_ret = close.pct_change().fillna(0.0)
    strategy_ret = position * asset_ret
    return strategy_ret
