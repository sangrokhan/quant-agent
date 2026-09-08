"""Strategy: Quarters Theory round-number level bounce (mean-reversion).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
"Quarters Theory" (FX Replay / various forex-education sources, read via
Google's synthesized overview of Investopedia/FXReplay/TradingView pages
for the query "quarters theory trading strategy specific rules") holds that
major round-number price levels ("big figures") and the quarter-points
between them (25%/50%/75%) act as psychological support/resistance where
institutional orders cluster, because round numbers are salient anchors for
both retail and algorithmic order placement. The source's own rules: plot
horizontal levels at the big figure and at 25/50/75% quarter marks; trade a
mean-reversion BOUNCE when price touches/wicks through a quarter level and
shows rejection (closes back on the near side), targeting the next quarter
level; stop just past the level tested.

First price-level/round-number strategy in this repo -- mechanically
distinct from all prior indicator-based or volatility-regime constructions:
the edge (if any) comes purely from where the raw price level sits relative
to a fixed round-number grid, not from any derived oscillator/moving
average. Adapted from FX pip-grids (which use a fixed price-unit spacing,
e.g. every 0.0025 for EURUSD) to a scale-invariant equivalent that works
across both equity ($400-scale) and crypto ($30k-100k-scale) prices: the
"big figure" spacing is defined as `round_size_pct` (a percentage of the
rolling `price_ref_window`-day average price), recomputed periodically
rather than a single fixed dollar amount, so the grid density stays
comparable in relative terms across assets and over time as price levels
drift.

Operationalized on daily bars:
    1. Round size = `round_size_pct` * rolling `price_ref_window`-day mean
       close (recomputed each bar, no lookahead beyond that trailing mean).
    2. Big figure = the nearest multiple of that round size at or below the
       prior close (no lookahead: uses yesterday's close to avoid using
       today's own high/low that generated the signal).
    3. Quarter levels = big_figure + {0, 0.25, 0.5, 0.75, 1.0} * round_size.
    3. Bullish bounce signal: today's low dips to within `wick_tolerance`
       (fraction of round_size) below/at a quarter level, AND today's close
       reclaims back above that level (rejection candle), AND RSI(rsi_window)
       was below `rsi_oversold` at some point in the last 2 bars (source's
       oscillator confirmation layer).
    4. Entry: next day's open (approximated here as next bar's close for a
       simple vectorized position series).
    5. Exit: price reaches the next quarter level above (target), closes
       below the tested level minus `stop_buffer_frac`*round_size (stop), or
       `max_hold_days` time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    round_size_pct: float = 0.05,
    price_ref_window: int = 60,
    wick_tolerance_frac: float = 0.03,
    rsi_window: int = 14,
    rsi_oversold: float = 35.0,
    stop_buffer_frac: float = 0.02,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series for the Quarters Theory
    round-number bounce strategy described in the module docstring."""
    df = _prep(price_df)
    close, low = df["close"], df["low"]
    n = len(df)
    rsi = _rsi(close, rsi_window)

    ref_price = close.rolling(price_ref_window, min_periods=price_ref_window).mean()
    round_size_series = round_size_pct * ref_price
    prev_close = close.shift(1)
    quarter_offsets = np.array([0.0, 0.25, 0.5, 0.75, 1.0])

    position = pd.Series(0, index=df.index, dtype=int)
    active_end = -1
    start = max(rsi_window, price_ref_window)

    for i in range(start, n):
        if i <= active_end:
            continue
        round_size = round_size_series.iloc[i]
        pc = prev_close.iloc[i]
        if not (np.isfinite(round_size) and round_size > 0 and np.isfinite(pc)):
            continue
        big_figure = np.floor(pc / round_size) * round_size
        tol = wick_tolerance_frac * round_size
        stop_buf = stop_buffer_frac * round_size
        levels = big_figure + quarter_offsets * round_size
        today_low = low.iloc[i]
        today_close = close.iloc[i]

        # Recent RSI oversold confirmation (today or yesterday).
        recent_oversold = (rsi.iloc[max(0, i - 1):i + 1] <= rsi_oversold).any()
        if not recent_oversold:
            continue

        # Find a quarter level that today's low touched/wicked through
        # (within tolerance) while today's close reclaimed above it.
        touched_level = None
        for lvl in levels:
            if (today_low <= lvl + tol) and (today_close > lvl):
                touched_level = lvl
                break
        if touched_level is None:
            continue

        # Target: next quarter level strictly above the touched level.
        above_levels = levels[levels > touched_level]
        if len(above_levels) == 0:
            continue
        target = above_levels[0]
        stop = touched_level - stop_buf

        entry_i = i + 1
        if entry_i >= n:
            continue

        exit_i = min(n - 1, entry_i + max_hold_days)
        for m in range(entry_i, min(n, entry_i + max_hold_days + 1)):
            if close.iloc[m] >= target or close.iloc[m] <= stop:
                exit_i = m
                break
        else:
            exit_i = min(n - 1, entry_i + max_hold_days)

        position.iloc[entry_i:exit_i + 1] = 1
        active_end = exit_i

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
