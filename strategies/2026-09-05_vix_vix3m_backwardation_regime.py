"""Strategy: VIX/VIX3M term-structure backwardation regime filter (equity/crypto).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-028):
The VIX/VIX3M ratio is the standard signal for the VIX futures term
structure regime: ratio < 1.0 means the curve is in contango (normal,
~80% of days), ratio >= 1.0 means backwardation (acute market stress --
near-term fear priced above medium-term). Per
https://volatilitybox.com/research/vix-contango-backwardation/, sustained
backwardation historically coincides with the worst equity drawdowns
(2008, 2011, 2020 COVID), and -- more actionably -- the *transition back*
from backwardation to contango (the ratio falling back below 1.0 after
having been >= 1.0) has historically been a strong buy signal for
equities, since it indicates acute fear is subsiding.

This strategy is distinct from the previously-rejected yield-curve
un-inversion (2026-09-05-024), HYG/LQD credit-spread (2026-09-05-025), and
DXY 50d SMA (2026-09-05-026) macro regime filters: this one uses the
options-market volatility term structure itself (not bond/credit/FX
proxies) as the risk-on/off signal.

Signal logic
------------
- ratio = close(^VIX) / close(^VIX3M).
- "backwardation" regime when ratio >= backwardation_threshold (default
  1.0).
- Long entry: ratio crosses back below backwardation_threshold after
  having been in backwardation within the last recovery_lookback days
  (curve normalizing back to contango = "fear subsiding" buy signal).
- Also stay long by default whenever NOT in backwardation and not
  freshly recovering from one (i.e. default long-bias filter, flat only
  while actively in backwardation) -- this tests both the "flat during
  acute stress" defensive framing and the "buy the normalization" timing
  framing in one rule: flat while ratio >= threshold, long otherwise,
  with an added cooldown/hold after the flip.
- Exit: ratio rises back to/above backwardation_threshold (re-enter
  backwardation), or after max_hold_days as a safety stop is NOT applied
  here (this is a regime-following filter, not a mean-reversion trade,
  so no fixed hold cap -- position tracks the regime state directly).

Note: ^VIX/^VIX3M ratio is a market-wide (SPX options) risk regime
signal, applied here to whatever `price_df` symbol is passed in (the
regime filter is asset-agnostic by design, same as the DXY/credit-spread
precedents in this repo) -- the traded asset's OWN price series is used
only for the return calc, the regime comes from a fixed VIX/VIX3M fetch
inside the module.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402

_vix_ratio_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _get_vix_ratio(start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Fetch ^VIX / ^VIX3M ratio series covering [start, end], cached."""
    key = (start.date().isoformat(), end.date().isoformat())
    if key in _vix_ratio_cache:
        return _vix_ratio_cache[key]

    fetch_start = datetime(max(start.year - 1, 2000), 1, 1, tzinfo=timezone.utc)
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    vix = load_equity("^VIX", fetch_start, fetch_end)
    vix3m = load_equity("^VIX3M", fetch_start, fetch_end)

    vix = vix.set_index(pd.to_datetime(vix["timestamp"], utc=True))["close"]
    vix3m = vix3m.set_index(pd.to_datetime(vix3m["timestamp"], utc=True))["close"]

    ratio = (vix / vix3m).dropna()
    ratio = ratio[~ratio.index.duplicated(keep="first")].sort_index()
    _vix_ratio_cache[key] = ratio
    return ratio


def generate_signals(
    price_df: pd.DataFrame,
    backwardation_threshold: float = 1.0,
    recovery_lookback: int = 10,
    min_hold_days: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series based on the VIX/VIX3M regime."""
    df = _prep(price_df)
    idx = df.index

    ratio_full = _get_vix_ratio(idx.min(), idx.max())
    # Align to asset's trading calendar via forward-fill (VIX indices trade
    # on the same NYSE calendar as equities; for crypto's 24/7 calendar we
    # forward-fill the last known VIX ratio value across non-trading gaps).
    ratio = ratio_full.reindex(idx, method="ffill")
    ratio = ratio.bfill()  # cover any leading NaNs

    in_backwardation = ratio >= backwardation_threshold

    position = pd.Series(0, index=idx, dtype=int)
    was_in_backwardation_recently = False
    days_since_recovery = 999999
    for i in range(len(idx)):
        currently_back = bool(in_backwardation.iloc[i])
        if currently_back:
            was_in_backwardation_recently = True
            days_since_recovery = 0
            position.iloc[i] = 0
        else:
            if was_in_backwardation_recently and days_since_recovery <= recovery_lookback:
                # In the recovery window after backwardation: require a
                # short min_hold before counting as a stable long (avoid
                # whipsaw right at the threshold).
                days_since_recovery += 1
                position.iloc[i] = 1 if days_since_recovery >= min_hold_days else 0
            else:
                was_in_backwardation_recently = False
                position.iloc[i] = 1
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
