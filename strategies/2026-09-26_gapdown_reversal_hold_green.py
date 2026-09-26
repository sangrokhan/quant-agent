"""Strategy: SPY "Simplest Gap-Down Reversal" (buy the weak open, hold until green).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-010):
Per SetupAlpha's "The SIMPLEST Gap-Down Reversal Trading Strategy of All
Time" (https://setup4alpha.substack.com/p/the-simplest-gap-down-reversal-trading,
disclosed public rule -- full RealTest script/param details paywalled):
"Buy SPY when the next regular-session open is below the previous
regular-session low." No filters (no RSI/MA/volatility gate) -- one entry
condition. Exit: hold until SPY "prints a green day" (close > that day's
own open, i.e. a green candle) -- adapted here to the standard convention
used across this repo's session-based strategies (close > prior close is
the more common "green day" proxy elsewhere in this KB; the source's own
phrase is ambiguous between the two, so this strategy implements BOTH via a
`green_day_definition` param, defaulting to the more literal single-bar
green-candle interpretation: close > that bar's own open).

Distinct from every existing gap-family entry in this repo:
- 2026-09-03-010 (academic gap-down fade): SAME-DAY trade only (buy open,
  sell that day's own close), a size-thresholded gap, no multi-day hold.
- 2026-09-08-001/-016 (gap+IBS+RSI combos, gap-fill target-based exits):
  require a bounded gap-size band AND an oversold IBS/RSI confirmation
  filter, exit at a fractional gap-fill price target intraday.
This entry has NO threshold on gap size (any open below the prior day's
low qualifies) and NO oscillator/trend filter -- and its exit is a
multi-day hold until the first green day, not a same-day or partial-target
exit. Source's own note: this "did not beat buy-and-hold" outright but
earned a "similar MAR while being invested only 21.46% of the time" -- a
capital-efficiency claim tested here directly via the standard validator
Sharpe/MDD/TC-survival stack rather than MAR/efficiency framing.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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
    green_day_definition: str = "close_gt_open",  # or "close_gt_prior_close"
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    low = df["low"]

    entry = open_ < low.shift(1)

    if green_day_definition == "close_gt_prior_close":
        exit_green_day = close > close.shift(1)
    else:
        exit_green_day = close > open_

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_green_day.iloc[i]) or held >= max_hold_days:
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
