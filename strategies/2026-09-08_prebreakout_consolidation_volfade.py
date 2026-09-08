"""Strategy: Pre-Breakout Consolidation (tight range near highs + fading volume).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-137):
Per https://www.investorstack.in/help/tech-pre-breakout-consolidation's
disclosed scanner rule: a stock "qualifies" for a pre-breakout setup when
(1) it's within `near_high_pct` (source: ~3%) of its `lookback_window`-day
(source: 100-day) high, (2) that high has NOT been broken in the last
`hold_window` (source: 30) days (the ceiling is holding, i.e. genuinely
consolidating rather than freshly making new highs), and (3) volume is
FADING during the consolidation (source: "volume is fading... that
combination, price near a ceiling that refuses to break and falling
volume, is classic accumulation"). Long entry triggers when a later close
finally breaks above that held ceiling.

This is DISTINCT from the two existing consolidation-breakout constructions
in this repo: Darvas Box (2026-09-05-054, a new high followed by
confirm_days NOT exceeding it, no volume condition) and Rectangle
(2026-09-08-111, a tight <=8% range with a MIDPOINT stop rule, no volume
condition either). The volume-fading-during-consolidation requirement is
this strategy's distinguishing, source-disclosed rule -- operationalized
as the consolidation window's average volume being below its own trailing
average (volume declining relative to its own recent history), rather than
a fixed absolute liquidity floor (the source's own ₹50/₹500cr/50k-share
floors are India-market-specific and not meaningfully portable).

Signal logic
------------
- Rolling `lookback_window`-day high (default 100).
- Consolidation confirmed at bar t when: close is within `near_high_pct`
  (default 0.03) of that rolling high, AND the rolling high has not been
  exceeded in the trailing `hold_window` days (default 30), AND the
  average volume over `hold_window` days is below `vol_fade_ratio` (default
  1.0) times the average volume over the PRIOR `hold_window`-day window
  (genuine volume fade, not just any volume level).
- Entry (long): the first bar after a confirmed consolidation where close
  breaks above the held ceiling (the rolling high recorded at
  confirmation).
- Exit: close falls back below the ceiling (breakout failed/reabsorbed),
  or a `max_hold_days` time-stop, whichever comes first.
- Flat otherwise.

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
    lookback_window: int = 100,
    near_high_pct: float = 0.03,
    hold_window: int = 30,
    vol_fade_ratio: float = 1.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    # Use the PRIOR bar's trailing high (excludes today's own close) as the
    # "ceiling" level, so a breakout (close > ceiling) is actually possible.
    rolling_high_excl_today = close.shift(1).rolling(lookback_window).max()
    near_high = close >= rolling_high_excl_today * (1 - near_high_pct)

    # "That high has not been broken in the last hold_window days": the
    # ceiling recorded hold_window bars ago is (at least) as high as
    # today's ceiling, i.e. no NEW high has been set in that window.
    ceiling_held = rolling_high_excl_today.shift(hold_window) >= rolling_high_excl_today

    recent_avg_vol = volume.rolling(hold_window).mean()
    prior_avg_vol = volume.shift(hold_window).rolling(hold_window).mean()
    volume_fading = recent_avg_vol < (vol_fade_ratio * prior_avg_vol)

    consolidation_confirmed = near_high.fillna(False) & ceiling_held.fillna(False) & volume_fading.fillna(False)
    ceiling_price = rolling_high_excl_today  # the held ceiling level to break above

    was_at_or_below_ceiling = close.shift(1) <= ceiling_price
    now_above_ceiling = close > ceiling_price

    # Entry requires: a consolidation was confirmed recently (within
    # hold_window bars, so we're still in that setup) AND a fresh breakout.
    consolidation_recent = consolidation_confirmed.rolling(hold_window, min_periods=1).max().astype(bool)
    entry = consolidation_recent.shift(1).fillna(False) & was_at_or_below_ceiling.fillna(False) & now_above_ceiling.fillna(False)

    exit_below_ceiling = close < ceiling_price

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_below_ceiling.iloc[i]) or held >= max_hold_days:
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
