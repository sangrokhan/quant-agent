"""Strategy: Copper/Gold Ratio (CGR) absolute-level regime gate for
corporate-bond-proxy / broad-index trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-XXX):
Per Jay Kaeppel / SentimenTrader's "Copper/Gold Ratio signals for metals,
miners and bonds" (2022-08-08,
https://sentimentrader.com/blog/coppergold-ratio-signals-for-metals-miners-and-bonds),
the Copper/Gold Ratio (CGR = close(HG=F copper futures) / close(GC=F gold
futures)) crossing ABOVE a fixed absolute level of 0.20 has historically
preceded above-average forward returns for investment-grade (LQD) and
high-yield (HYG) corporate bond ETFs; CGR dropping below 0.19 preceded
strength in metals/miners instead. This is a genuinely different
construction from the two prior copper/gold-ratio variants already tested
in this repo: 2026-09-05-031/032 used a rolling z-score of the ratio
(regime-relative, not absolute) and 2026-09-10-039 gated on the ratio being
above its own trailing SMA (also relative, not a fixed level). Here we test
the SentimenTrader source's own DISCLOSED FIXED ABSOLUTE THRESHOLD directly
as a trend-confirmation gate: stay long the primary asset (e.g. LQD/HYG as
bond proxies, or QQQ/SPY as a broader risk-on proxy) only while (a) its own
price is in an uptrend (close > SMA(trend_window)) AND (b) CGR is at/above
the disclosed absolute crossing level (default 0.20) -- i.e. treat "CGR
above 0.20" as a standing risk-on regime confirmation rather than a one-off
event-study trigger. Below 0.20, go flat (the source's own data showed weak
average forward returns for these assets below that level). No crypto
analogue exists for the copper/gold futures ratio; the crypto leg degrades
to a plain SMA trend-follow as an explicit, documented robustness check,
not the genuine tested hypothesis (same convention as 2026-09-20-049/050).

Signal logic
------------
- ratio = close(HG=F) / close(GC=F), fetched via data/loaders.py.
- risk_on_regime = ratio >= cgr_threshold (absolute level, default 0.20).
- trend_up = close(primary) > SMA(close(primary), trend_window).
- Entry/hold (long): trend_up AND risk_on_regime.
- Exit: either condition breaks (flat).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
        price_df is the PRIMARY symbol's OHLCV frame; the CGR leg is
        fetched internally for equity asset_class only.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402

_ratio_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _get_ratio(start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Fetch HG=F/GC=F close ratio series covering [start, end], cached."""
    key = (start.date().isoformat(), end.date().isoformat())
    if key in _ratio_cache:
        return _ratio_cache[key]

    fetch_start = datetime(max(start.year - 2, 2000), 1, 1, tzinfo=timezone.utc)
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    copper = load_equity("HG=F", fetch_start, fetch_end)
    gold = load_equity("GC=F", fetch_start, fetch_end)

    copper = copper.set_index(pd.to_datetime(copper["timestamp"], utc=True))["close"]
    gold = gold.set_index(pd.to_datetime(gold["timestamp"], utc=True))["close"]

    # SentimenTrader's disclosed CGR scale (0.19/0.20 absolute thresholds)
    # uses copper priced in CENTS/lb (COMEX convention) over gold priced in
    # $/oz -- yfinance HG=F returns copper in DOLLARS/lb, so multiply by 100
    # to match the source's scale (raw $/lb over $/oz gives ~0.0017-0.0027,
    # nowhere near the disclosed 0.19-0.20 threshold).
    ratio = ((copper * 100.0) / gold).dropna()
    ratio = ratio[~ratio.index.duplicated(keep="first")].sort_index()
    _ratio_cache[key] = ratio
    return ratio


def generate_signals(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    trend_window: int = 100,
    cgr_threshold: float = 0.20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    sma = close.rolling(trend_window).mean()
    trend_up = (close > sma).fillna(False)

    if asset_class == "equity":
        ratio_full = _get_ratio(df.index.min(), df.index.max())
        ratio = ratio_full.reindex(df.index, method="ffill").bfill()
        risk_on_regime = ratio >= cgr_threshold
    else:
        # No copper/gold futures-ratio analogue in crypto -- gate is
        # always True, degrading to a plain SMA trend-follow for the
        # crypto asset class (explicit, documented simplification).
        risk_on_regime = pd.Series(True, index=df.index)

    position = (trend_up & risk_on_regime).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    trend_window: int = 100,
    cgr_threshold: float = 0.20,
) -> pd.Series:
    """Return the strategy's daily return series."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        asset_class=asset_class,
        trend_window=trend_window,
        cgr_threshold=cgr_threshold,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
