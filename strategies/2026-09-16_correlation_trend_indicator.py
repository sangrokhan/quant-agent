"""Strategy: Correlation Trend Indicator (CTI, LuxAlgo) regime gate + trend-follow.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
LuxAlgo's Correlation Trend Indicator (CTI) computes the Pearson correlation
coefficient over a rolling window (default 20 bars) between the price
series (close) and an "ideal rising line" (i.e. the bar index 0..N-1,
representing a perfectly steady linear advance). Readings near +1 mean the
window closely tracked a steady up-move; near -1 a steady down-move; near 0
a trendless/choppy window. Per LuxAlgo's own disclosed trading rule: above
+0.5 = bullish trend regime (worth trend-following), below -0.5 = bearish
regime, inside the band = neutral/no-trade. This is distinct from every
other trend-strength gate already tested in this repo (ADX, Choppiness
Index, VHF, Random Walk Index, Trend Persistence Range) since CTI is a
literal Pearson correlation between price and a straight line, not a
directional-movement or range-based construction.

Signal logic
------------
- Long (position=1) whenever CTI (Pearson r between close and bar-index
  over `length` bars) is above `trend_threshold` (default 0.5).
- Flat (position=0) otherwise (neutral/choppy or bearish regime) -- this
  repo trades long-only.
- Optional max_hold_days safety cap.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rolling_pearson_vs_index(close: pd.Series, length: int) -> pd.Series:
    """Pearson correlation of close[t-length+1..t] against 0..length-1 (an
    'ideal rising line'), computed per-window via a rolling apply.
    """
    idx = np.arange(length, dtype=float)
    idx_mean = idx.mean()
    idx_centered = idx - idx_mean
    idx_ss = (idx_centered ** 2).sum()

    def _corr(window: np.ndarray) -> float:
        if np.isnan(window).any():
            return np.nan
        y = window - window.mean()
        denom = np.sqrt((y ** 2).sum() * idx_ss)
        if denom == 0:
            return 0.0
        return float((idx_centered * y).sum() / denom)

    return close.rolling(length).apply(_corr, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 20,
    trend_threshold: float = 0.5,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series from the CTI regime gate."""
    df = _prep(price_df)
    close = df["close"]
    cti = _rolling_pearson_vs_index(close, length)
    position = (cti > trend_threshold).astype(int)
    position = position.fillna(0)

    if max_hold_days and max_hold_days > 0:
        pos = position.values.copy()
        hold = 0
        for i in range(len(pos)):
            if pos[i] == 1:
                hold += 1
                if hold > max_hold_days:
                    pos[i] = 0
                    hold = 0
            else:
                hold = 0
        position = pd.Series(pos, index=position.index)

    return position.reindex(df.index).fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    length: int = 20,
    trend_threshold: float = 0.5,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        df, length=length, trend_threshold=trend_threshold, max_hold_days=max_hold_days
    )
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
