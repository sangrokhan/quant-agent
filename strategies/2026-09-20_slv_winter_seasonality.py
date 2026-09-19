"""Strategy: SLV (Silver ETF) winter-months seasonality.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-062):
Per QuantifiedStrategies.com's "Best Silver Trading Strategy | Rules,
Settings, And Backtest" (https://www.linkedin.com/pulse/best-silver-trading-strategy-rules-settings-backtest-srrlf,
visited this iteration via browser_exec fallback -- web_search DDGS
backend hit repeated TLS/connection-reset errors this iteration), the
article's disclosed seasonality section states: "Silver contracts, like
gold, have been found to perform quite well in the winter months.
Performance during spring and fall is mixed. It does poorly during the
summer." (The article's own separately-referenced day-trading strategy
with specific entry/exit rules is explicitly withheld -- "we won't reveal
the trading rules and settings" -- and is NOT implemented here; only the
qualitative winter-seasonality finding, which the source does disclose,
is tested.)

Mechanical rule: long SLV during the "winter months" (interpreted as
Dec-Feb, the standard meteorological/calendar winter, per the source's own
side-by-side "winter / spring / summer / fall" framing), flat the rest of
the year.

First SLV/silver-specific strategy in this repo (0 prior "Silver" or "SLV"
symbol entries found); distinct from all Gold-seasonality entries already
tested (which use GLD, not SLV, and generally different month windows).

Source: https://www.linkedin.com/pulse/best-silver-trading-strategy-rules-settings-backtest-srrlf
(qualitative seasonality claim disclosed in free content; the article's
own specific day-trading strategy rules are explicitly paywalled/withheld
and not reconstructed here).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: 1 long/0 flat)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    winter_months: tuple = (12, 1, 2),
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    month = close.index.month
    is_winter = pd.Series([m in winter_months for m in month], index=close.index)
    position = is_winter.astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
