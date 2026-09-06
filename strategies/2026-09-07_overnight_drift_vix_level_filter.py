"""Strategy: Overnight-only drift, gated by an elevated VIX level filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-020):
Per the NY Fed staff report "The Overnight Drift" (Boyarchenko, Larsen,
Whelan; https://www.newyorkfed.org/medialibrary/media/research/staff_reports
/sr917.pdf, read via Google search-result AI-overview + snippet synthesis
since the PDF itself is JS/paywall-blocked to web_extract): average
overnight returns (prior close -> next open) are higher following days with
GREATER end-of-day VIX levels, consistent with an end-of-day order-imbalance/
inventory-risk-premium theory of overnight drift. This repo already tested
the UNCONDITIONAL overnight-hold anomaly (2026-09-03-007: accepted QQQ,
near-miss SPY, rejected crypto) with no VIX filter at all. This iteration
adds an explicit VIX-level-elevated gate (VIX close > its own rolling
median over vix_lookback days, by more than vix_regime_ratio) so the
strategy only holds overnight on nights the source's own research says the
drift premium should be structurally stronger, skipping calm-VIX nights
that plain unconditional-hold would trade into unnecessarily. Crypto is
tested as a falsification check (no VIX index, no discrete session
boundary -- expected to fail or be non-sensical, same as the prior
overnight-anomaly test).

Signal logic
------------
- Compute daily overnight return: (today's open - yesterday's close) /
  yesterday's close.
- VIX close (for equities) or the underlying asset's own realized vol proxy
  (for crypto, since there's no VIX-equivalent) is compared to its own
  trailing `vix_lookback`-day rolling median; "elevated" when current VIX
  >= vix_regime_ratio * that trailing median.
- Position for day t = 1 (i.e. earn day t's overnight return, entered at
  t-1's close) only when yesterday's close-of-day VIX/vol-proxy reading was
  elevated per the above; else flat overnight and flat intraday too (no
  intraday exposure at all -- pure overnight anomaly capture, matching
  2026-09-03-007's convention).
- No separate stop/exit -- this is a 1-day hold structurally (overnight
  only), so max_hold_days is not applicable here; the elevated-VIX gate
  itself is the only tunable filter parameter besides vix_lookback.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position,
        1 meaning "held overnight into this day's open")

Note: `price_df` is the tradable asset (QQQ/SPY/BTC-USDT/ETH-USDT). VIX
data is fetched internally via data/loaders.load_equity("^VIX", ...) for
equities, aligned to price_df's date range, per this repo's established
VIX-strategy pattern (see strategies/2026-09-05_vix_rsi2_connors_alvarez.py).
For crypto there is no VIX; we fall back to the asset's own 20d realized
vol as the "elevated regime" proxy, matching this repo's other crypto
VIX-fallback strategies.
"""

from __future__ import annotations

import os
import sys
from datetime import timezone

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fetch_vix(index: pd.DatetimeIndex) -> pd.Series | None:
    try:
        start = index.min().to_pydatetime()
        end = index.max().to_pydatetime()
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        vix = _prep(load_equity("^VIX", start, end))
        return vix["close"]
    except Exception:
        return None


def _vol_regime_series(df: pd.DataFrame) -> pd.Series:
    """VIX close if available (equities); else the asset's own 20d realized
    vol (annualized) as a fallback proxy (crypto, no VIX)."""
    vix_close = _fetch_vix(df.index)
    if vix_close is not None and vix_close.notna().sum() > 30:
        return vix_close.reindex(df.index).ffill()

    import math

    close = df["close"]
    log_ret = (close / close.shift(1)).apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    return log_ret.rolling(20).std() * (252 ** 0.5)


def generate_signals(
    price_df: pd.DataFrame,
    vix_lookback: int = 60,
    vix_regime_ratio: float = 1.15,
) -> pd.Series:
    """Return a {0,1} position series: 1 = held overnight into this row's open."""
    df = _prep(price_df)
    vol_proxy = _vol_regime_series(df)
    vol_median = vol_proxy.rolling(vix_lookback, min_periods=max(10, vix_lookback // 3)).median()
    elevated = (vol_proxy >= vol_median * vix_regime_ratio).fillna(False)

    # Signal is based on YESTERDAY's close-of-day reading (elevated y'day ->
    # hold overnight into TODAY's open). Shift the elevated flag by 1 so the
    # position on day t reflects information known at t-1's close.
    position = elevated.shift(1).fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Overnight-only strategy returns: on days with position=1, earn that
    day's (open_t - close_{t-1}) / close_{t-1} return; else 0 (flat both
    overnight and intraday, matching 2026-09-03-007's convention)."""
    df = _prep(price_df)
    if "open" not in df.columns:
        raise ValueError("price_df must have an 'open' column for overnight-return strategies")
    close = df["close"]
    open_ = df["open"]
    overnight_ret = (open_ - close.shift(1)) / close.shift(1)
    overnight_ret = overnight_ret.fillna(0.0)

    position = generate_signals(price_df, **params)
    strategy_ret = position * overnight_ret
    return strategy_ret
