"""Strategy: Multi-day-pullback short-term reversal with volatility-adjusted
sizing and a FIXED short holding period (1 or 3 days), gated by a 200-day
trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://www.advancedinvesting.org/testing-an-ai-assisted-research-workflow-for-multi-asset-pullback-strategy-discovery/
(IAIM summary of Quantpedia/Sona Beluska's "Testing an AI-Assisted Research
Workflow for Multi-Asset Pullback Strategy Discovery"): a systematic
short-term reversal strategy across 6 liquid ETFs (equities, fixed income,
currencies, gold, commodities), 2006-2025, pairs a 200-day MA trend filter
with a multi-day pullback trigger, volatility-adjusted sizing, and
equal-weighted allocation. The source's own headline numbers: best spec
(200-day MA filter, 2-day pullback, 1-day hold) delivered Sharpe ~0.95
while invested <50% of the time; a more conservative 3-day-pullback variant
gave comparable returns to buy-and-hold with ~2.4x smaller max drawdown
(-13.69% vs -33.28%) while deployed only ~21% of the time. Source reports
no alpha decay across sub-periods (2021-2025 was the strongest, Sharpe
1.25) and win rates >56% throughout.

This is a structurally new signal for this repo: prior "pullback" family
entries (50+ hits) almost all use SIGNAL-BASED exits (indicator crossing
back, trend-filter break, price recovering above some MA/level) — this one
uses the source's own FIXED short holding period (1 or 3 trading days,
matching its own disclosed best specs) combined with an explicit
VOLATILITY-ADJUSTED position size (inverse-vol sizing, distinct from every
prior binary 0/1 pullback entry in this repo).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  (continuous [0,1]
        position-size series, not strictly binary, due to vol-adjusted
        sizing -- still {0, sized-weight} per the interface's spirit)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, causal -- entries decided using data known as of the
        entry day's own close, held forward hold_days with no look-ahead)
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
    pullback_days: int = 2,
    hold_days: int = 1,
    vol_window: int = 20,
    target_vol: float = 0.15,
    max_leverage: float = 1.0,
) -> pd.Series:
    """Return a [0, max_leverage] continuous position-size series.

    Entry condition (evaluated at each day's close, using only that day's
    own and prior known data): close > SMA(trend_window) (established
    uptrend) AND the asset has closed down on each of the last
    `pullback_days` consecutive days (a short pullback within the trend).
    On a qualifying day, a position sized by inverse realized volatility
    (target_vol / trailing `vol_window`-day annualized realized vol,
    capped at max_leverage) is held for the NEXT `hold_days` trading days
    (a fixed holding period, not a signal-based exit).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_sma = close.rolling(trend_window).mean()
    above_trend = (close > trend_sma).fillna(False)

    daily_change = close.diff()
    down_day = (daily_change < 0).fillna(False)
    consecutive_down = down_day.rolling(pullback_days).sum() == pullback_days

    entry_signal = (above_trend & consecutive_down).fillna(False)

    daily_ret = close.pct_change()
    realized_vol = (daily_ret.rolling(vol_window).std() * (252 ** 0.5)).fillna(0.0)
    # Avoid divide-by-zero; where realized_vol is 0, size defaults to 0
    # (can't size a position off an undefined vol estimate).
    vol_scale = (target_vol / realized_vol.replace(0.0, float("nan"))).clip(upper=max_leverage)
    vol_scale = vol_scale.fillna(0.0)

    entry_size = (entry_signal.astype(float) * vol_scale)

    # Hold each entry's sized position for the next `hold_days` trading
    # days starting the day AFTER entry (no look-ahead: the entry signal
    # is known at entry day's close, position taken from next day's open
    # onward via next-day return application in generate_returns).
    position = pd.Series(0.0, index=close.index)
    n = len(close)
    entry_idx = [i for i, v in enumerate(entry_signal.values) if v]
    for i in entry_idx:
        size = entry_size.iloc[i]
        for h in range(1, hold_days + 1):
            j = i + h
            if j < n:
                position.iloc[j] = max(position.iloc[j], size)

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Daily close-to-close strategy returns: position[t] * (close[t]/close[t-1] - 1).

    position[t] already reflects a decision made using data known as of
    day t-1 (see generate_signals: position is set for days AFTER the
    entry-signal day), so no additional shift is needed here.
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = (position * daily_ret).fillna(0.0)
    strat_returns.name = "strategy_returns"
    return strat_returns
