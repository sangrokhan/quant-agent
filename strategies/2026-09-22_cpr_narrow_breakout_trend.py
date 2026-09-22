"""Strategy: Central Pivot Range (CPR) breakout with narrow-CPR trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-064):
Per Groww's "Central Pivot Range (CPR): Intraday Trading Strategy Guide"
(https://groww.in/blog/central-pivot-range, read via browser_exec this
iteration -- web_search's DDGS backend intermittently TLS-erroring), the
Central Pivot Range is a 3-line range derived from the PRIOR period's
high/low/close: Pivot P=(H+L+C)/3, Bottom Central BC=(H+L)/2, Top Central
TC=2P-BC. Source's disclosed rule: "If the current market price moves above
the top central level, it indicates an uptrend... ideal time to place buy
orders... CPR acts as a support level" and conversely below BC signals a
downtrend. Source further states a NARROW CPR (TC-BC small relative to
price, meaning price compressed near the pivot the prior period) signals a
higher-probability trend day ahead, while a WIDE CPR favors range-bound/
reversal behavior instead. Adapted here from the source's intraday framing
to daily bars (prior DAY's H/L/C computes today's CPR levels, adapted
directly per this repo's convention for other pivot-family indicators
e.g. Camarilla/Woodie's). First Central Pivot Range strategy in this repo
(0 prior KB hits).

Signal logic
------------
- Compute CPR from the PRIOR bar's H/L/C: P=(H+L+C)/3, BC=(H+L)/2, TC=2P-BC.
- CPR width = (TC - BC) / P (normalized). Narrow CPR: width < narrow_pctile
  (source's compressed-range -> trend-day preference), computed as a
  rolling percentile of recent widths.
- Long entry: close crosses above TC (breakout, source's own disclosed buy
  trigger) AND CPR is narrow (source's own trend-day preference filter).
- Exit: close crosses back below the Pivot P (trend has failed, source's
  own mid-level), OR a max_hold_days time-stop.
- Flat otherwise. Long-only (no short per SAFETY.md scope).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def generate_signals(
    price_df: pd.DataFrame,
    width_lookback: int = 60,
    narrow_pctile: float = 0.4,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    high = df["high"].shift(1)
    low = df["low"].shift(1)
    close_prior = df["close"].shift(1)

    pivot = (high + low + close_prior) / 3.0
    bc = (high + low) / 2.0
    tc = 2 * pivot - bc

    width = (tc - bc).abs() / pivot
    width_rank = width.rolling(width_lookback, min_periods=20).apply(
        lambda x: (x < x.iloc[-1]).sum() / len(x) if len(x) > 0 else float("nan"), raw=False
    )
    narrow = (width_rank <= narrow_pctile).fillna(False)

    close = df["close"]
    breakout = (close > tc).fillna(False)
    entry_trigger = (breakout & narrow).fillna(False)
    exit_trigger_level = (close < pivot).fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = -1
    for i in range(len(df.index)):
        if not in_position:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                entry_idx = i
        else:
            held = i - entry_idx
            if bool(exit_trigger_level.iloc[i]) or held >= max_hold_days:
                in_position = False
        position.iloc[i] = 1 if in_position else 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    width_lookback: int = 60,
    narrow_pctile: float = 0.4,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        df,
        width_lookback=width_lookback,
        narrow_pctile=narrow_pctile,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
