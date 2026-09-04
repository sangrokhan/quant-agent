"""Strategy: VIX term-structure "buy the relief" -- long SPY when the
VIX/VIX3M ratio flips DOWN from backwardation (panic) back into contango
(calm).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-157):
The VIX term structure (ratio of the 30-day VIX to the 3-month VIX3M)
compresses market fear into one number: ratio < 1.0 = contango (calm,
longer-term fear priced higher than near-term), ratio > 1.0 =
backwardation (panic, near-term fear spikes above longer-term). Per
Options Cafe's VIX term-structure article (17 years of VIX/VIX3M data,
2005-2026), buying the initial spike into backwardation is "a coin flip",
but buying the RELIEF -- the moment the ratio crosses back down through
1.0 from backwardation into contango -- is claimed to substantially
improve short-horizon SPY win rate. This is distinct from the previously-
rejected VIX-Bollinger-Band mean-reversion strategy (2026-09-04-103, which
used a single VIX series' own 20d Bollinger Band spike as the trigger) --
here the signal comes from comparing TWO points on the vol curve (VIX vs
VIX3M), not a single series' own historical range.

Signal logic
------------
- Fetch VIX (^VIX) and VIX3M (^VIX3M) daily closes via data/loaders.py
  load_equity, aligned to the SPY price_df's index.
- ratio = VIX_close / VIX3M_close.
- Backwardation state: ratio > 1.0. Contango state: ratio <= 1.0.
- Long entry ("buy the relief"): ratio crosses back down through 1.0
  (was > 1.0 yesterday, is <= 1.0 today) -- i.e. the panic spike is
  resolving.
- Exit: after a fixed short holding period (relief_hold_days, default 5,
  per source's "88% bet in just five trading days" framing) OR if the
  ratio spikes back above a re-panic_threshold (>1.0 again, renewed panic
  invalidates the relief thesis), whichever comes first.
- Flat (no position) whenever not in an active long. This strategy never
  requires the underlying (SPY/QQQ) to be in any particular trend -- it is
  purely a vol-relief timing signal.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1} position series
    generate_returns(price_df, **params) -> pd.Series daily strategy returns

Note: this strategy is equity-index-specific by construction (VIX/VIX3M
only price S&P 500 implied vol) -- it is not meaningfully testable on
crypto pairs (no analogous term-structure data available via this repo's
loaders), so the Step 6 grid for this strategy is equity-only (QQQ, SPY).
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


def _vix_ratio(index: pd.DatetimeIndex) -> pd.Series:
    """Fetch VIX and VIX3M and compute the ratio, aligned to `index`."""
    from data.loaders import load_equity  # local import: avoid hard dep at module import time
    start = index.min() - pd.Timedelta(days=10)
    end = index.max() + pd.Timedelta(days=2)
    if start.tzinfo is not None:
        start = start.tz_localize(None)
    if end.tzinfo is not None:
        end = end.tz_localize(None)
    vix = load_equity("^VIX", start.to_pydatetime(), end.to_pydatetime())
    vix3m = load_equity("^VIX3M", start.to_pydatetime(), end.to_pydatetime())
    vix = vix.set_index("timestamp")["close"] if "timestamp" in vix.columns else vix["close"]
    vix3m = vix3m.set_index("timestamp")["close"] if "timestamp" in vix3m.columns else vix3m["close"]
    vix = vix.reindex(index).ffill()
    vix3m = vix3m.reindex(index).ffill()
    return vix / vix3m


def generate_signals(
    price_df: pd.DataFrame,
    relief_hold_days: int = 5,
    backwardation_threshold: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ratio = _vix_ratio(close.index)
    backwardation = ratio > backwardation_threshold
    relief_entry = (~backwardation) & backwardation.shift(1).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            re_panic = bool(backwardation.iloc[i]) if not pd.isna(backwardation.iloc[i]) else False
            if held >= relief_hold_days or re_panic:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(relief_entry.iloc[i]):
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
