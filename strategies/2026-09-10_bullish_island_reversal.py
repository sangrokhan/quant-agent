"""Strategy: Bullish Island Reversal (gap-down / range cluster / gap-up), long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-XXX):
Per https://www.investopedia.com/terms/i/islandreversal.asp (Gordon Scott/
Investopedia, "Island Reversal: Key Characteristics & Examples"): an island
reversal is a stock chart pattern where two price gaps in opposite
directions isolate a cluster of trading days from the surrounding trend.
Source's disclosed 5 characteristics: (1) a lengthy prior trend, (2) an
initial "breakaway" gap, (3) a cluster of days trading within a definable
range (the "island"), (4) increased volume near the gaps/during the island,
(5) a final "exhaustion" gap in the opposite direction that isolates the
island. This implementation operationalizes the BULLISH variant (island
bottom, per the source's stated bearish/bullish symmetry): prior downtrend
(close < SMA(trend_window)) -> a gap-down day (today's high < yesterday's
low) -> an island cluster of 1-max_island_days days trading below that
gap-down day's low -> a gap-up day (today's low > the island's own high AND
> the original gap-down day's high, clearing the whole isolated cluster) ->
long entry on the gap-up confirmation day's close. Exit on a close back
below the island's low (failed reversal) or a max_hold_days time-stop.
First candlestick-gap-based ISLAND reversal strategy in this repo --
distinct from all prior single-gap (gap-down-fade, weekday-gap-continuation)
and non-gap swing-pattern (Turtle Soup, SFP, RSI Failure Swing) strategies
since this requires the specific TWO-GAP isolation structure the source
defines.

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


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    max_island_days: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series (bullish island reversal)."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    n = len(close)

    sma_trend = close.rolling(trend_window).mean()
    downtrend = (close < sma_trend).fillna(False)

    # Detect gap-down days: today's high < yesterday's low.
    gap_down = (high < low.shift(1)).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    island_low = None

    i = 0
    while i < n:
        if in_position:
            held = i - entry_idx
            if bool(close.iloc[i] < island_low) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                i += 1
                continue
            position.iloc[i] = 1
            i += 1
            continue

        # Look for a fresh island-bottom setup starting at a gap-down day
        # that occurred within an existing downtrend.
        if bool(gap_down.iloc[i]) and bool(downtrend.iloc[i]):
            gap_down_high = high.iloc[i]
            gap_down_low = low.iloc[i]
            island_high = gap_down_high
            island_low_running = gap_down_low
            found_entry = None
            for k in range(1, max_island_days + 1):
                j = i + k
                if j >= n:
                    break
                # While still inside the island (below the gap-down day's low),
                # track the island's own high/low range.
                if high.iloc[j] < low.iloc[j - 1]:
                    # A further gap-down extends/resets the island start -- stop
                    # scanning this candidate (handled by outer loop next pass).
                    break
                island_high = max(island_high, high.iloc[j])
                island_low_running = min(island_low_running, low.iloc[j])
                # Check for the confirming gap-up: today's low clears above
                # BOTH the island's own high-so-far AND the original gap-down
                # day's high, isolating the whole cluster.
                if low.iloc[j] > island_high and low.iloc[j] > gap_down_high:
                    found_entry = j
                    break
            if found_entry is not None:
                position.iloc[found_entry] = 1
                in_position = True
                entry_idx = found_entry
                island_low = island_low_running
                i = found_entry + 1
                continue
        position.iloc[i] = 0
        i += 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
