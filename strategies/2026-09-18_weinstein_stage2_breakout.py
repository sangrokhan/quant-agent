"""Strategy: Stan Weinstein Stage 2 Breakout (30-week SMA regime + volume-confirmed resistance breakout).

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD, sourced from
Google SERP snippets aggregating multiple corroborating descriptions of
Stan Weinstein's "Stage Analysis" -- MQL5's "Automating Classic Market
Methods (Part 3): Stan Weinstein Stage Analysis" EA description, and
ThinkCapital/TrendSpider's Weinstein Stage 2 Breakout strategy summaries,
read via browser_exec after web_search's DDGS backend RequestError'd):

Weinstein's four-stage market cycle (Base/Stage-1, Advancing/Stage-2,
Top/Stage-3, Declining/Stage-4) is defined relative to a 30-week (=150
trading-day) simple moving average. First HMA/Weinstein-Stage-Analysis
entry in this repo (0 prior KB hits for "Stan Weinstein"/"Stage Analysis").
Disclosed mechanical rule (consistent across all corroborating sources):

- Stage 2 ENTRY (long): price closes above a prior resistance level
  (rolling N-bar high, i.e. breaking out of the Stage-1 base) on volume
  at least `volume_confirm_mult`x the recent average volume, AND the
  30-week SMA is itself trending upward (not flat/declining) -- confirms
  the breakout occurs in a genuinely advancing regime, not a false start
  out of a still-basing/declining trend.
- Stage 3 EXIT: price closes back below the 30-week SMA on above-average
  ("heavy") volume, OR the 30-week SMA itself flattens/turns down after
  a sustained advance (SMA slope crossing from positive to
  non-positive) -- whichever fires first.

Economic rationale (per Weinstein's own thesis, echoed by every source):
almost all of a stock's/index's sustained gain occurs during Stage 2; the
combination of a rising long-term trend filter + volume-confirmed
resistance breakout aims to enter near the START of that stage rather than
mid-trend, and exit at the first credible sign of Stage 3 distribution
rather than riding the full round-trip back down.

Distinct from this repo's existing SMA-trend-following and Donchian/
resistance-breakout strategies since it REQUIRES the volume confirmation
AND the SMA-slope-positive gate jointly (not either alone), and its exit
condition is a compound "close-below-SMA-on-heavy-volume OR SMA-flattens"
rule rather than a simple crossover or fixed time-stop.

Interface contract for validators (see validation/validators.py) and
grid_test.py (Step 6): generate_signals/generate_returns both accept
tunable parameters as keyword arguments.
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
    sma_window: int = 150,  # ~30 weeks of trading days
    sma_slope_lookback: int = 10,
    resistance_window: int = 50,
    volume_avg_window: int = 50,
    volume_confirm_mult: float = 2.0,
    exit_volume_mult: float = 1.5,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry (Stage 2 breakout): close breaks above the trailing
    resistance_window-bar high (excluding today) on volume >=
    volume_confirm_mult x trailing volume_avg_window-bar average volume,
    AND the sma_window SMA has a positive slope over sma_slope_lookback
    bars.
    Exit (Stage 3 signal): close drops below the SMA on volume >=
    exit_volume_mult x average volume, OR the SMA's slope turns
    non-positive after having been positive.
    """
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    sma = close.rolling(sma_window, min_periods=sma_window // 2).mean()
    sma_slope = sma - sma.shift(sma_slope_lookback)
    sma_rising = sma_slope > 0

    avg_vol = volume.rolling(volume_avg_window, min_periods=volume_avg_window // 2).mean()
    resistance = close.rolling(resistance_window).max().shift(1)

    breakout = close > resistance
    vol_confirm_entry = volume >= (volume_confirm_mult * avg_vol)
    entry = breakout & vol_confirm_entry & sma_rising.fillna(False)

    below_sma = close < sma
    vol_confirm_exit = volume >= (exit_volume_mult * avg_vol)
    exit_heavy_vol = below_sma & vol_confirm_exit
    exit_sma_flatten = (sma_slope <= 0) & (sma_slope.shift(1) > 0).fillna(False)
    exit_ = (exit_heavy_vol | exit_sma_flatten).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
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
