"""Strategy: Crypto Fear & Greed Index contrarian threshold hysteresis.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-029):
Per alternative.me's free, unauthenticated Fear & Greed Index API
(https://api.alternative.me/fng/), a daily 0-100 crypto market sentiment
composite (volatility, momentum/volume, social media, surveys, dominance,
Google Trends) has been published since Feb 2018 (verified via direct curl:
3149 daily observations from timestamp 1517443200 through the present).
Prior entries in this repo (2026-09-12-167 and others) incorrectly marked
put/call-ratio-style sentiment indices as "feasibility-blocked, no data
source" -- that block was correct for the CBOE options put/call ratio
(genuinely no free source) and MVRV/on-chain metrics (genuinely
unavailable), but the crypto Fear & Greed Index specifically IS freely
fetchable via a simple unauthenticated HTTP GET, distinct from those. This
is the first strategy in this repo to actually use this data source.

Classic contrarian framing (widely disclosed across LuxAlgo/TradingView/
Investopedia-style summaries of this exact index): readings <=25 =
"Extreme Fear" (capitulation, contrarian buy zone), readings >=75 =
"Extreme Greed" (euphoria, contrarian exit/reduce zone). This strategy
implements a two-level hysteresis state machine on those exact index
values (reusing this repo's already-validated VIX/DXY absolute-level
hysteresis construction, 2026-09-20-009/026): go/stay long once the index
closes at or below `enter_level` (extreme fear), hold regardless of
intermediate wiggles until the index closes at or above `exit_level`
(extreme greed), then flat until fear returns.

Tested on crypto (BTC/USDT, ETH/USDT) where the index is directly
economically relevant, AND on equity (QQQ, SPY) as an explicit
falsification check (the index measures CRYPTO-specific sentiment, so an
equity-index reaction would be a coincidental/spurious cross-asset
correlation rather than the intended mechanism).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)
"""

from __future__ import annotations

import json
import urllib.request

import numpy as np
import pandas as pd

_fng_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fetch_fear_greed() -> pd.Series:
    """Fetch the FULL history of the alternative.me Fear & Greed Index
    (free, unauthenticated, ~3100+ daily observations since Feb 2018).
    Cached in-process across calls (matches this repo's existing
    _dxy_cache/_vix in-process caching convention for auxiliary series,
    e.g. strategies/2026-09-20_dxy_absolute_level_hysteresis_regime.py)."""
    if "fng" in _fng_cache:
        return _fng_cache["fng"]

    url = "https://api.alternative.me/fng/?limit=0&format=json"
    with urllib.request.urlopen(url, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    records = payload["data"]
    idx = pd.to_datetime([int(r["timestamp"]) for r in records], unit="s", utc=True)
    values = pd.Series([float(r["value"]) for r in records], index=idx).sort_index()
    values.index = values.index.normalize()
    _fng_cache["fng"] = values
    return values


def _hysteresis_state(fng: pd.Series, enter_level: float, exit_level: float) -> pd.Series:
    """Two-level hysteresis: once index closes AT/BELOW enter_level (extreme
    fear), state flips to 1 (long) and stays 1 regardless of intermediate
    values until index closes AT/ABOVE exit_level (extreme greed), then
    flips to 0 (flat) and stays 0 until fear returns."""
    arr = fng.to_numpy()
    n = len(arr)
    state = np.zeros(n, dtype=int)
    cur = 0
    for i in range(n):
        v = arr[i]
        if np.isnan(v):
            state[i] = cur
            continue
        if cur == 0 and v <= enter_level:
            cur = 1
        elif cur == 1 and v >= exit_level:
            cur = 0
        state[i] = cur
    return pd.Series(state, index=fng.index)


def generate_signals(
    price_df: pd.DataFrame,
    enter_level: float = 25.0,
    exit_level: float = 75.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series driven by the crypto Fear &
    Greed Index's own absolute-level two-level hysteresis, reindexed/ffilled
    onto the traded asset's own daily index (per-asset price_df supplied by
    the grid/validator harness -- same index applies to both equity and
    crypto legs to test the falsification hypothesis)."""
    df = _prep(price_df)
    fng = _fetch_fear_greed()

    fng_reindexed = fng.reindex(df.index, method="ffill")
    position = _hysteresis_state(fng_reindexed, enter_level, exit_level)
    position.index = df.index
    return position.astype(int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
