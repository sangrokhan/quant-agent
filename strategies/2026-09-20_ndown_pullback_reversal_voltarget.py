"""Strategy: N-Day Pullback Reversal with 200-day trend filter + inverse-vol sizing.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per Quantpedia's "Testing an AI-Assisted Research Workflow for Multi-Asset
Pullback Strategy Discovery" (https://quantpedia.com/testing-an-ai-assisted-research-workflow-for-multi-asset-pullback-strategy-discovery/,
summarized via https://www.advancedinvesting.org/testing-an-ai-assisted-research-workflow-for-multi-asset-pullback-strategy-discovery/
after the direct quantpedia.com URL redirected to the homepage -- browser_exec
fallback, web_search DDGS backend TLS/connection-reset errors this
iteration), a systematic short-term reversal strategy across six liquid
ETFs (equities, fixed income, currencies, gold, commodities, 2006-2025):
pairs a 200-day moving-average TREND FILTER with a MULTI-DAY PULLBACK
TRIGGER (N consecutive down days) and volatility-adjusted position sizing.
Source's own best specification (200-day MA trend filter, 2-day pullback,
1-day hold) delivered Sharpe ~0.95 (nearly double the best passive
benchmark) while invested less than half the time; the edge is
concentrated almost entirely in the FIRST day after entry. A more
conservative 3-day-pullback variant gave a similar return to buy-and-hold
with 2.4x smaller drawdown (-13.69% vs -33.28%) and best-in-class Calmar,
deploying only ~21% of capital. Sub-period tests (source's own) showed no
alpha decay -- the most recent window (2021-2025) was the strongest on
record (Sharpe 1.25).

Adapted here to this repo's single-symbol equity/crypto universe (QQQ,
SPY, BTC/USDT, ETH/USDT): long when close > SMA(200) (trend filter) AND
the asset has closed down on each of the trailing `pullback_days` days
(the "N consecutive down days" pullback trigger), hold for `hold_days`
trading days (source's own tested 1-day and multi-day hold variants),
position size scaled by `target_vol`/trailing realized vol (this repo's
standard inverse-vol sizing overlay, matching the source's own
"volatility-adjusted sizing" element, capped at `max_leverage`). Distinct
from every other pullback-continuation construction already in this repo
(Fibonacci retracement uses a %-retracement-of-swing measure; DiNapoli
uses a forward-displaced MA touch; Bollinger middle-band uses distance
from the SMA basis) -- this is the first strategy to use a pure COUNT of
consecutive down-closes (no magnitude/indicator threshold at all) as the
pullback trigger, combined with a fixed short holding period rather than
an indicator-based exit.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
"""

from __future__ import annotations

import math

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
    pullback_days: int = 2,
    hold_days: int = 1,
) -> pd.Series:
    """Return a {0,1} long/flat position series (before vol-target sizing;
    the {0,1} series is used by generate_returns to also compute exposure).
    """
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    trend_filter = close > sma

    daily_up = close.diff() > 0
    daily_down = close.diff() < 0
    # N consecutive down days: rolling window of the last `pullback_days`
    # daily changes are ALL down.
    consecutive_down = daily_down.rolling(pullback_days).sum() == pullback_days

    entry_trigger = (consecutive_down & trend_filter).shift(1).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    countdown = 0
    for i in range(len(close)):
        if countdown > 0:
            position.iloc[i] = 1
            countdown -= 1
        elif entry_trigger.iloc[i]:
            position.iloc[i] = 1
            countdown = hold_days - 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    pullback_days: int = 2,
    hold_days: int = 1,
    vol_window: int = 20,
    target_vol: float = 0.15,
    max_leverage: float = 1.0,
) -> pd.Series:
    """Position-weighted daily returns with inverse-vol sizing while in a
    signaled trade (no transaction costs applied here).
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, trend_window=trend_window, pullback_days=pullback_days, hold_days=hold_days
    )

    daily_ret = close.pct_change()
    realized_vol = daily_ret.rolling(vol_window).std() * math.sqrt(252)
    # Inverse-vol sizing dial, capped at max_leverage: when realized vol is
    # very low, exposure is capped at max_leverage rather than blowing up.
    exposure = (target_vol / realized_vol).clip(upper=max_leverage).fillna(0.0)

    strategy_ret = position.shift(1).fillna(0) * exposure.shift(1).fillna(0) * daily_ret.fillna(0.0)
    return strategy_ret
