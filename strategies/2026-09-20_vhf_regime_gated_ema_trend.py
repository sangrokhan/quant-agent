"""Strategy: Vertical Horizontal Filter (VHF, Adam White) regime-gated EMA trend-follower.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-077):
Per a Google AI-overview synthesis (TrendSpider/cTrader/Incredible Charts;
browser_exec fallback -- web_search DDGS backend returns mangled
non-English results this iteration), the Vertical Horizontal Filter (Adam
White) is a DIRECTION-BLIND regime-detection indicator that measures how
"vertical" (trending) vs "horizontal" (ranging/congested) recent price
action has been, using the ratio of net directional displacement to total
path length traveled. Standard formula (confirmed via Incredible
Charts/TradingView/Google AI-overview):
    VHF = (HighestClose_n - LowestClose_n) / sum(|Close_i - Close_i-1|, n)
with default n=28. High VHF (>0.30-0.50) indicates a trending regime; low
VHF (<0.15-0.30) indicates ranging/congestion. Since VHF itself cannot tell
uptrend from downtrend, the disclosed rule pairs it as a REGIME GATE with a
directional tool: go long only when VHF is above a trend threshold (regime
confirms a genuine trend is underway, filtering out whipsaw-prone ranging
periods) AND price crosses above a baseline EMA (direction trigger); exit
when price crosses back below the EMA or VHF collapses (momentum loss).
This is a genuinely distinct construction from this repo's existing
volatility-regime filters (which use realized-vol terciles/ATR, not a
net-displacement-over-path-length ratio) and from all its EMA-crossover
strategies (which lack any trend/range regime pre-filter). 0 prior VHF
entries in this repo.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _vhf(close: pd.Series, period: int = 28) -> pd.Series:
    highest_close = close.rolling(period).max()
    lowest_close = close.rolling(period).min()
    numerator = (highest_close - lowest_close).abs()
    denominator = close.diff().abs().rolling(period).sum()
    return numerator / denominator.replace(0, pd.NA)


def generate_signals(
    price_df: pd.DataFrame,
    vhf_period: int = 28,
    vhf_threshold: float = 0.35,
    ema_period: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: VHF(vhf_period) > vhf_threshold (trending regime confirmed)
    AND close crosses above EMA(ema_period). Exit: close crosses back below
    the EMA, regardless of VHF state (a fresh trending regime could reverse
    direction; the crossover exit handles that).
    """
    df = _prep(price_df)
    close = df["close"]

    vhf = _vhf(close, period=vhf_period)
    ema = close.ewm(span=ema_period, adjust=False).mean()

    trending_regime = vhf > vhf_threshold
    above_ema = close > ema

    entry = trending_regime.fillna(False) & above_ema & (~above_ema.shift(1).fillna(False))
    stay = above_ema

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_vals = entry.values
    stay_vals = stay.values

    for i in range(len(close)):
        if in_position:
            if not bool(stay_vals[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
                in_position = True
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
