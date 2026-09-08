"""Strategy: Mayer Multiple contrarian accumulation, BTC/USDT daily bars.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-127):
The Mayer Multiple (close / 200-day SMA) is a well-known Bitcoin valuation
heuristic (Trace Mayer, popularized via
https://www.theinvestorspodcast.com/bitcoin-mayer-multiple/): historically,
a multiple >= 2.4x has marked overheated/late-cycle conditions that
subsequently mean-revert, while a multiple below the long-run historical
average (~1.47x, i.e. price close to or below its 200-day trend) marks
comparatively cheap accumulation zones. This strategy tests a systematic,
long-only, time-series version of that heuristic: go long when the Mayer
Multiple is in/below a "cheap" band (accumulation), and de-risk to flat
when it spikes into the "overheated" band (>= upper threshold), rather than
holding through the entire cycle unconditionally (distinct from the
already-tested 2026-09-03-002 BTC absolute/trailing-return momentum, which
is a trend-following idea with no valuation-band component, and distinct
from 2026-09-04-XXX BTC halving-500-day-rule, which is a fixed calendar
rule referencing halving dates rather than a continuously-computed
price/SMA ratio).

Signal logic
------------
- Mayer Multiple: mm(t) = close(t) / SMA_200(close)(t).
- Entry (long): mm(t) <= entry_threshold (default 1.47, the historical
  average multiple cited by the source -- i.e. price at or below its
  typical premium over the 200d trend, a relatively cheap/accumulation
  zone) AND mm(t) is available (t >= 200 bars in).
- Exit: mm(t) >= exit_threshold (default 2.4, the source's cited
  overheated/euphoria threshold) -- de-risk to flat when the multiple
  spikes into blow-off territory, OR a max_hold_days time-stop (avoid
  indefinite unconditional buy-and-hold masquerading as a signal).
- Flat otherwise (no position held between exits and the next entry
  trigger).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
Both accept tunable parameters as keyword arguments per RESEARCH_LOOP.md
Step 5's grid-test contract.
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
    sma_window: int = 200,
    entry_threshold: float = 1.47,
    exit_threshold: float = 2.4,
    max_hold_days: int = 180,
) -> pd.Series:
    """Return a {0,1} long/flat position series based on the Mayer Multiple."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(sma_window).mean()
    mayer_multiple = close / sma

    entry = mayer_multiple <= entry_threshold
    exit_overheated = mayer_multiple >= exit_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        mm_valid = pd.notna(mayer_multiple.iloc[i])
        if in_position:
            held = i - entry_idx
            if (mm_valid and bool(exit_overheated.iloc[i])) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if mm_valid and bool(entry.iloc[i]):
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
