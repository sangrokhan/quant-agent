"""Strategy: VIX/VIX3M term-structure regime reversion (end of backwardation
buy signal) for equity indices.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-025):
Per volatilitybox.com's VIX term-structure guide
(https://volatilitybox.com/research/vix-contango-backwardation/), the
VIX/VIX3M ratio is the standard actionable contango/backwardation signal:
ratio < 1.0 = normal contango, ratio >= 1.0 = backwardation (acute market
stress, historically coincident with severe equity drawdowns: -57% in
2008-09, -19% in Aug 2011, -34% in Mar 2020). Critically, the source states
"the end of backwardation (when the curve normalizes back to contango) has
historically been a strong buy signal for equities" -- i.e. the transition
FROM ratio>=1.0 back TO ratio<1.0 is the entry trigger, not backwardation
itself (which is a warning, not a buy signal per the source).

This is a distinct regime-transition signal from the two other VIX
strategies already in this repo: CVR3 (2026-09-05-021, VIX-only 3-condition
same-day pattern vs its own 10d SMA) and Connors/Alvarez VIX RSI
(2026-09-05-052, 2-period RSI spike on VIX itself). Neither of those uses
the VIX/VIX3M term-structure RATIO at all.

Signal logic
------------
- Compute vix_ratio = VIX close / VIX3M close (requires a second price
  series for VIX3M, passed in via the `vix3m_df` kwarg by the caller --
  grid_test's generic (price_df, **params) signature doesn't support a
  second data source cleanly, so this strategy fetches VIX3M internally via
  data/loaders.load_equity("^VIX3M", ...) aligned to price_df's own index
  range, keeping the public generate_signals/generate_returns contract
  intact (single price_df positional arg).
- Backwardation flag: vix_ratio >= backwardation_threshold (default 1.0).
- Entry (long the underlying equity index): backwardation flag flips from
  True (yesterday) to False (today) -- i.e. the ratio crosses back below
  the threshold (end of backwardation).
- Exit: vix_ratio rises back to/above exit_threshold (regime reverts to
  stress, default same as backwardation_threshold), OR a max_hold_days
  time-stop.

Interface contract for validators (see validation/validators.py /
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_vix_ratio(index: pd.DatetimeIndex) -> pd.Series:
    """Fetch VIX and VIX3M and compute the ratio, aligned to `index`."""
    import sys
    import os

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    if data_dir not in sys.path:
        sys.path.insert(0, data_dir)
    from loaders import load_equity  # noqa: E402

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    # pad start earlier to allow shift/rolling warmup upstream if needed
    vix_df = load_equity("^VIX", start, end)
    vix3m_df = load_equity("^VIX3M", start, end)

    vix = _prep(vix_df)["close"]
    vix3m = _prep(vix3m_df)["close"]

    ratio = (vix / vix3m).reindex(index).ffill()
    return ratio


def generate_signals(
    price_df: pd.DataFrame,
    backwardation_threshold: float = 1.0,
    exit_threshold: float = 1.0,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    try:
        vix_ratio = _load_vix_ratio(close.index)
    except Exception:
        # VIX data unavailable for this symbol's date range/asset class
        # (e.g. crypto -- no VIX-equivalent) -> flat throughout.
        return pd.Series(0, index=close.index, dtype=int)

    backwardation = (vix_ratio >= backwardation_threshold).fillna(False)
    prev_backwardation = backwardation.shift(1).fillna(False)
    entry_signal = prev_backwardation & (~backwardation)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = None
    idx_list = close.index

    for i in range(len(idx_list)):
        if not in_position:
            if bool(entry_signal.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
        else:
            held_days = i - entry_idx
            ratio_val = vix_ratio.iloc[i]
            regime_reverted = bool(ratio_val >= exit_threshold) if pd.notna(ratio_val) else False
            if regime_reverted or held_days >= max_hold_days:
                position.iloc[i] = 0
                in_position = False
                entry_idx = None
            else:
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    backwardation_threshold: float = 1.0,
    exit_threshold: float = 1.0,
    max_hold_days: int = 40,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs applied)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        backwardation_threshold=backwardation_threshold,
        exit_threshold=exit_threshold,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
