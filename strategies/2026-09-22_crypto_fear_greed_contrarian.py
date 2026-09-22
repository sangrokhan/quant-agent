"""Strategy: Crypto Fear & Greed Index contrarian mean-reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-104):
alternative.me's daily Crypto Fear & Greed Index (FNG, 0-100, blending BTC
volatility/momentum/social-media/dominance/surveys) reflects broad
crypto-market sentiment. Per the source's own stated thesis ("extreme fear
can be a sign investors are too worried -- a buying opportunity; extreme
greed means the market is due for a correction"), this strategy goes long
when FNG drops to/below an "extreme fear" threshold and exits once
sentiment normalizes back above an exit threshold (or after a max holding
period). Distinct from this repo's prior Fear & Greed attempts, which were
rejected at the FEASIBILITY-BLOCKED novelty-check stage ("no data source");
this iteration confirms api.alternative.me/fng/ is a free, no-auth JSON API
with full history back to 2018-02-01, so the hypothesis is now testable.

Data note
---------
FNG is fetched directly from api.alternative.me (a supplementary sentiment
series, not OHLCV price data, so this bypasses data/loaders.py per its own
docstring scope) and cached in-process for the life of the Python process
(module-level cache) so a grid-test sweep across many param combos only
hits the network once. The index is BTC-market-derived; applied here both
to crypto pairs (direct sentiment on the asset traded) and, as a
"broad risk-sentiment" proxy, to equity index ETFs (QQQ/SPY) to test
whether crypto-sentiment extremes also predict equity mean reversion
(a weaker, secondary hypothesis).

Signal logic
------------
- Long entry: FNG value <= extreme_fear_threshold (default 20 == "Extreme
  Fear" per alternative.me's own classification bands).
- Exit: FNG value >= exit_threshold (default 50 == back to "Neutral"), OR
  a max holding period of max_hold_days trading days (avoid indefinite
  holds through a slow grind that never clearly recovers).
- Flat otherwise. Long-only (no short leg -- extreme-greed short-selling is
  a separate, riskier hypothesis not tested here).
"""

from __future__ import annotations

import pandas as pd

_fng_cache: pd.Series | None = None


def _load_fng_series() -> pd.Series:
    """Fetch+cache the full daily Fear & Greed Index history as a pandas
    Series indexed by UTC-normalized date (00:00), values 0-100."""
    global _fng_cache
    if _fng_cache is not None:
        return _fng_cache

    import requests

    resp = requests.get("https://api.alternative.me/fng/?limit=0&format=json", timeout=20)
    resp.raise_for_status()
    data = resp.json()["data"]
    idx = pd.to_datetime([int(d["timestamp"]) for d in data], unit="s", utc=True).tz_localize(None).normalize()
    vals = pd.Series([float(d["value"]) for d in data], index=idx, name="fng")
    vals = vals.sort_index()
    vals = vals[~vals.index.duplicated(keep="last")]
    _fng_cache = vals
    return vals


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _aligned_fng(price_index: pd.DatetimeIndex) -> pd.Series:
    fng = _load_fng_series()
    norm_index = pd.DatetimeIndex(price_index).tz_localize(None) if getattr(price_index, "tz", None) else pd.DatetimeIndex(price_index)
    norm_index = norm_index.normalize()
    # forward-fill FNG onto the price calendar (FNG updates once/day, price
    # bars may be daily or intraday; ffill within a day, no look-ahead since
    # each day's FNG value is published for that same UTC day at day-start).
    fng_ff = fng.reindex(fng.index.union(norm_index)).sort_index().ffill()
    aligned = fng_ff.reindex(norm_index)
    aligned.index = price_index
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    extreme_fear_threshold: float = 20.0,
    exit_threshold: float = 50.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    fng = _aligned_fng(close.index)

    entry = fng <= extreme_fear_threshold
    exit_sentiment = fng >= exit_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        fng_i = fng.iloc[i]
        if pd.isna(fng_i):
            position.iloc[i] = 1 if in_position else 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(exit_sentiment.iloc[i]) or held >= max_hold_days:
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
