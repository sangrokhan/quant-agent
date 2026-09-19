"""Strategy: Gold/Silver Ratio RSI(5) pair signal, applied to GLD (single-asset).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-057):
Per quantifiedstrategies.com's "Gold Silver Chart Ratio Strategy: Trading
Rules and Backtest" (https://www.quantifiedstrategies.com/gold-silver-chart-ratio-strategy/,
visited this iteration via browser_exec fallback -- web_search DDGS backend
hit repeated TLS/connection-reset errors on every query attempted), the
gold/silver price ratio (GLD/SLV) is a classic intermarket indicator. Most
of the source's own numeric trading rules are paywalled, but ONE concrete
rule is disclosed in the free article body: "when the 5-day RSI is above 75
we buy gold (GLD) and sell short silver (SLV). We exit when the 5-day RSI
falls below 50." (RSI applied to the GLD/SLV ratio series itself, per the
article's context -- a momentum-following, not mean-reverting, signal, as
the source notes "the trading strategy buys on strength, the opposite of
mean reversion").

The source explicitly reports this pair trade as UNDERPERFORMING ("the
gold silver pair trade strategy shows a flat development") -- this
iteration tests that exact disclosed rule as a single-asset long/flat
strategy on GLD (rather than the pair-trade long-GLD/short-SLV
construction, since a market-neutral pair position isn't directly
expressible via this repo's single-symbol generate_signals/generate_returns
contract): long GLD when RSI(5) of the GLD/SLV ratio crosses above
rsi_entry (default 75), flat when RSI(5) of the ratio falls below
rsi_exit (default 50). GLD's own daily returns (not the pair spread) are
used for daily strategy returns, since a single-asset adaptation naturally
just holds/doesn't-hold GLD rather than running a hedged spread.

First Gold/Silver-Ratio strategy in this repo (0 prior "Gold Silver Ratio"
entries in strategies_index.jsonl before this iteration); distinct from
all prior Copper/Gold-ratio entries (different metals pair, different
threshold construction) and from the source's own explicit warning that
this exact rule underperforms in its native pair-trade form -- tested here
to confirm/refute that finding under this repo's single-asset framing and
grid/validator methodology, per RESEARCH_LOOP.md's requirement to ground
hypotheses in actually-read material rather than skip untested ideas.

Source: https://www.quantifiedstrategies.com/gold-silver-chart-ratio-strategy/
(fully disclosed rule text quoted above, read directly from the free
article body, not the paywalled "Trading Rules" section at the bottom).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: 1 long/0 flat)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)

NOTE on data contract: `price_df` here is expected to be GLD's OHLCV, and
this module internally fetches SLV via `data.loaders.load_equity` to build
the ratio series, following the established internal-basket-load pattern
used elsewhere in this repo (e.g. strategies/2026-09-08_pairs_zscore_cointegration.py).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def _load_ratio_denominator(index: pd.DatetimeIndex, denom_symbol: str) -> pd.Series:
    from loaders import load_equity  # local import so unit tests can monkeypatch

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    denom_df = load_equity(denom_symbol, start=start, end=end)
    denom_df = _prep(denom_df)
    return denom_df["close"].reindex(index).ffill()


def generate_signals(
    price_df: pd.DataFrame,
    denom_symbol: str = "SLV",
    rsi_period: int = 5,
    rsi_entry: float = 75.0,
    rsi_exit: float = 50.0,
    max_hold_days: int = 250,
) -> pd.Series:
    """Return a {0,1} long/flat position series (long GLD only)."""
    df = _prep(price_df)
    close = df["close"]

    denom_close = _load_ratio_denominator(close.index, denom_symbol)
    ratio = close / denom_close.replace(0.0, pd.NA)
    ratio = ratio.astype(float)

    rsi = _rsi(ratio, rsi_period)
    entry_cond = rsi > rsi_entry
    exit_cond = rsi < rsi_exit

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_now = bool(exit_cond.iloc[i]) if pd.notna(exit_cond.iloc[i]) else False
            if exit_now or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            entry_now = bool(entry_cond.iloc[i]) if pd.notna(entry_cond.iloc[i]) else False
            if entry_now:
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
