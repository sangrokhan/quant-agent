"""Strategy: Gold-Silver Ratio 80/50 tactical rotation signal, applied as a
regime gate on a primary asset's SMA trend-following signal.

Hypothesis (this cron trigger's iteration 2):
Per the widely-cited "80/50 rule" for gold-silver ratio trading (confirmed
via Google SERP synthesis this iteration -- CBS News/SprottMoney/JM
Bullion/GoldSilver/AuAg Funds/ICICI Direct/Dukascopy all independently
describe the same numeric rule: "When the ratio exceeds 80:1, gold is
likely overvalued [relative to silver]" (JM Bullion) and "investors shift
into silver when the ratio exceeds 80 and back into gold when it falls
near 50" (AuAg Funds) -- ratio = GLD_close / SLV_close as a proxy for the
raw gold:silver ounce ratio). This repo already has an accepted GLD/SLV
ratio z-score regime filter (2026-09-05-030), but that used a rolling
252-day z-score threshold, NOT the industry-standard fixed 80/50 absolute
thresholds -- this iteration tests the source-disclosed FIXED-LEVEL rule
directly (distinct construction: no rolling normalization, hard numeric
80/50 levels applied to the raw price ratio itself with hysteresis),
applied here as a risk-on/risk-off regime gate on the primary traded
asset's SMA trend-following signal (rather than trading GLD/SLV directly,
matching this repo's established pattern e.g. 2026-09-05-067 XLU/SPY,
2026-09-11-049 GDX/GLD): ratio > 80 (gold richly priced vs silver, per the
source's own framing this signals late-cycle risk-off/safe-haven-crowding)
gates the primary asset flat; ratio back down near/below 50 (or a
configurable reset level) re-enables trend-following exposure. Hysteresis
prevents whipsaw at either threshold.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)

Note: `price_df` is the PRIMARY traded asset's OHLCV (QQQ/SPY/BTC/ETH per
this repo's grid convention); GLD/SLV are fetched internally via
data/loaders.py::load_equity and aligned to price_df's index.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from loaders import load_equity


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _gold_silver_ratio(index: pd.DatetimeIndex) -> pd.Series:
    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    gld = load_equity("GLD", start=start, end=end)
    slv = load_equity("SLV", start=start, end=end)
    gld = _prep(gld)["close"]
    slv = _prep(slv)["close"]
    ratio = (gld / slv).reindex(index).ffill()
    return ratio


def _risk_on_state(ratio: pd.Series, high_thresh: float, low_thresh: float) -> pd.Series:
    """Hysteresis state machine: flat (risk-off) once ratio > high_thresh,
    re-enabled (risk-on) once ratio <= low_thresh; holds prior state between
    thresholds."""
    vals = ratio.to_numpy()
    state = np.ones_like(vals, dtype=bool)  # default risk-on until first signal
    current = True
    for i, v in enumerate(vals):
        if np.isnan(v):
            state[i] = current
            continue
        if v > high_thresh:
            current = False
        elif v <= low_thresh:
            current = True
        state[i] = current
    return pd.Series(state, index=ratio.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    high_thresh: float = 80.0,
    low_thresh: float = 50.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series: SMA trend-following on the
    primary asset, gated flat whenever the GLD/SLV price ratio is in its
    'risk-off' (ratio>high_thresh, not yet reset below low_thresh) state."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    ratio = _gold_silver_ratio(df.index)
    risk_on = _risk_on_state(ratio, high_thresh, low_thresh)

    position = (trend_long.fillna(False) & risk_on.fillna(True)).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    high_thresh: float = 80.0,
    low_thresh: float = 50.0,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        trend_window=trend_window,
        high_thresh=high_thresh,
        low_thresh=low_thresh,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
