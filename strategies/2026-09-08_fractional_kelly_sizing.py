"""Strategy: Fractional-Kelly-criterion dynamic position sizing overlay on an
SMA(200) trend gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-176):
Per JournalX "Kelly Criterion Position Sizing: Why Full Kelly Breaks Traders
(and What to Use Instead)" (https://journalx.app/blog/kelly-criterion-position-sizing),
the Kelly criterion f* = (b*p - q) / b (p = trailing win rate, q = 1-p, b =
avg win / avg loss) gives the theoretically growth-optimal fraction of
capital to risk, but "full Kelly" produces 50-80% drawdowns even with a
genuinely positive edge because Kelly optimizes only for long-run growth,
not path smoothness. The source's own recommendation is fractional Kelly
(25-50% of full Kelly) which "captures roughly three-quarters of the optimal
growth rate while cutting drawdowns roughly in half."

Adapted single-asset: use an SMA(trend_window) trend filter as the entry
signal (same base filter as prior position-sizing-overlay strategies
2026-09-08-165/174/175, isolating the SIZING mechanism as the tested
variable), then size each long position using a ROLLING trailing-window
estimate of Kelly's own p/b (win rate and average-win/average-loss ratio,
estimated from the strategy's own trailing trade history, strictly
no-lookahead) scaled by `kelly_fraction` (e.g. 0.25 = quarter Kelly, 0.5 =
half Kelly), clipped to [0, leverage_cap].

First Kelly-criterion-based position-sizing entry in this repo -- distinct
from the inverse-realized-vol-targeting overlay (2026-09-08-165, sizing
driven by volatility magnitude) and the CPPI running-max-drawdown-floor
overlay (2026-09-08-174/175, sizing driven by a path-dependent NAV cushion)
since Kelly sizing here is driven by the strategy's own trailing empirical
win-rate/payoff-ratio edge estimate, not price volatility or portfolio NAV.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series (weight,
        continuous exposure in [0, leverage_cap], same convention as
        2026-09-08-165/174/175).
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
    trend_window: int = 200,
    trade_history_window: int = 252,
    kelly_fraction: float = 0.25,
    leverage_cap: float = 1.0,
    min_trades_for_estimate: int = 10,
    default_weight: float = 0.5,
) -> pd.Series:
    """Return the fractional-Kelly exposure weight series (continuous, in
    [0, leverage_cap]).

    Kelly's p (win rate) and b (avg win / avg loss) are estimated from the
    strategy's OWN trailing `trade_history_window` days of the underlying
    asset's daily returns ON DAYS WHEN THE TREND FILTER WAS ACTIVE (i.e. the
    "trades" this strategy would have taken), strictly using data up to and
    including day t-1 only (no lookahead). Before `min_trades_for_estimate`
    qualifying days are available, use `default_weight` as a neutral
    placeholder sizing.
    """
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    uptrend = close > sma
    daily_ret = close.pct_change().fillna(0.0)

    # Only the days the trend filter would have been long count as "trades"
    # for Kelly's own trailing win-rate/payoff estimate.
    trade_ret = daily_ret.where(uptrend, other=pd.NA)

    weight = pd.Series(0.0, index=close.index)
    n = len(close)

    for i in range(n):
        if not bool(uptrend.iloc[i]):
            weight.iloc[i] = 0.0
            continue

        window_start = max(0, i - trade_history_window)
        # Strictly no-lookahead: only trades up to (not including) day i.
        hist = trade_ret.iloc[window_start:i].dropna()

        if len(hist) < min_trades_for_estimate:
            weight.iloc[i] = min(default_weight, leverage_cap)
            continue

        wins = hist[hist > 0]
        losses = hist[hist < 0]
        p = len(wins) / len(hist) if len(hist) else 0.0
        q = 1.0 - p
        avg_win = wins.mean() if len(wins) else 0.0
        avg_loss = abs(losses.mean()) if len(losses) else 0.0
        b = (avg_win / avg_loss) if avg_loss > 0 else 0.0

        if b <= 0:
            kelly_full = 0.0
        else:
            kelly_full = (b * p - q) / b

        target_w = kelly_fraction * kelly_full
        weight.iloc[i] = min(max(target_w, 0.0), leverage_cap)

    return weight


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    weight = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (weight.shift(1).fillna(0.0) * daily_ret)
    return strategy_ret
