"""Strategy: SMA trend-following gate with a Paroli-style (anti-Martingale)
positive-progression position-sizing overlay.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-258):
Per quantifiedstrategies.com's "Paroli Strategy in Trading" article
(https://www.quantifiedstrategies.com/paroli-strategy-in-trading/, read via
browser_exec this iteration -- web_search DDGS backend returned "No results
found" for this iteration's query), the Paroli / anti-Martingale system
increases bet size after a win and resets to the base unit after a loss
(commonly capped at 3 consecutive step-ups: 1 -> 2 -> 4 -> reset). The
source's own stated verdict is explicit and load-bearing for this
hypothesis: "Paroli can change the shape of returns, but it cannot create an
edge on its own... it only makes sense if the underlying strategy already
has positive expectancy." This repo already has an accepted directional
edge (SMA(200) trend-following gate, reused across 100+ sizing-overlay
strategies in this repo, e.g. 2026-09-13_cci_sizing_sma_trend.py) -- so this
iteration tests the source's own claim mechanically: does a Paroli-style
progression overlaid ON TOP of that existing edge improve/preserve
risk-adjusted performance relative to flat position sizing, or does it (as
the source's math argument implies) just reshape the path without
improving expected value, potentially just adding drawdown risk from
concentrated position sizing during losing streaks that follow winning
streaks?

Distinct from every other sizing-dial strategy in this repo (RSI/CCI/ATR/
TRIX/VQI/etc. continuous indicator-value-to-exposure mappings) -- this is
the first strategy in this repo where exposure is a function of the
STRATEGY'S OWN TRAILING REALIZED DAILY WIN/LOSS STREAK, not any price-
derived technical indicator. Also distinct from the many *_down_streak /
*_win_streak entry-TRIGGER strategies already tested (e.g.
2026-09-08-058, 2026-09-09-004) -- here the streak drives continuous
EXPOSURE SIZE while already in a position, not the entry/exit trigger
itself.

Signal logic
------------
- Base directional gate: long-candidate when close > SMA(trend_window)
  (identical construction to every other *_sizing_sma_trend.py in this
  repo, e.g. 2026-09-13_cci_sizing_sma_trend.py).
- While trend-long, track a capped positive-progression multiplier on the
  day's own (gated) daily return sign, evaluated causally day-by-day
  (t-1 return sign decides day t's exposure -- no look-ahead):
    * Start each new trend-long episode (or after a losing day) at
      base_unit exposure.
    * After a winning day (previous day's position-weighted return > 0),
      step exposure up by a factor of `step_multiplier` (e.g. 2x), capped
      at `max_steps` consecutive step-ups (e.g. 3 -> 1x -> 2x -> 4x -> 8x,
      matching the source's own capped-at-3-wins convention).
    * After a losing day (previous day's position-weighted return <= 0),
      reset exposure back to base_unit (source's own literal Paroli reset
      rule).
  All exposures are clipped to `leverage_cap` (crypto-safe hard ceiling,
  same convention as this repo's leverage-cap-aware strategies).
- Flat (0 exposure) whenever not in the SMA trend-long regime.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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
    trend_window: int = 200,
    base_unit: float = 0.5,
    step_multiplier: float = 2.0,
    max_steps: int = 3,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    trend_long = (close > close.rolling(trend_window).mean()).fillna(False)

    n = len(close)
    exposure = pd.Series(0.0, index=close.index)
    steps = 0  # current consecutive-win step count, 0..max_steps

    for i in range(n):
        if not bool(trend_long.iloc[i]):
            exposure.iloc[i] = 0.0
            steps = 0
            continue

        # Determine this bar's exposure from the PRIOR bar's realized
        # (gated, position-weighted) return sign -- causal, no look-ahead.
        if i == 0 or not bool(trend_long.iloc[i - 1]):
            # Fresh entry into a trend-long episode: start at base unit.
            steps = 0
        else:
            prev_exposure = exposure.iloc[i - 1]
            prev_gated_ret = prev_exposure * daily_ret.iloc[i - 1]
            if prev_gated_ret > 0:
                steps = min(steps + 1, max_steps)
            else:
                steps = 0

        raw_exposure = base_unit * (step_multiplier ** steps)
        exposure.iloc[i] = min(raw_exposure, leverage_cap)

    return exposure


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
