"""Strategy: Pre-3-day-weekend / pre-holiday effect, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-020),
sourced from Google's AI-overview summary + QuantifiedStrategies.com search
snippet for "Do Stocks Rise Or Drop Before A 3-day Weekend?" (the specific
article page itself 404'd when fetched directly, but the search-result
snippet gave a concrete, quotable rule): "Stocks rise before US 3-day
weekends. Pre-holiday returns beat random trading days. Strategy buys
Thursday, sells Friday. Backtest covers S&P 500 since 1960." The AI
overview additionally described the general pre-holiday-effect mechanism:
"equities tend to post above-average returns with low volatility on the
final trading day before major public holidays," entering "at the market
close on the trading day right before a major market holiday," attributed
to reduced institutional selling pressure/lower liquidity around holidays.

Rather than hardcoding a fixed list of US market holidays (which the
source's Thursday-before-3-day-weekend framing implicitly encodes), this
implementation detects the effect data-natively and more generally: for
each trading day present in the price series, check the CALENDAR gap to
the next trading day present in the same series. If that gap is >= 3
calendar days (i.e. the next bar is not the very next weekday --
indicating a holiday or long weekend sits between them), treat today as a
"pre-holiday" day and go long from today's close to the next trading
day's close. This works directly off whatever trading calendar the data
loader already encodes (US market holidays for equity, no holidays at all
for 24/7 crypto -- crypto is included purely as a falsification check,
since a 24/7 market has no closure-driven liquidity effect to test).

This is a new calendar-anomaly signal for this repo -- distinct from
turn-of-month (2026-09-03-006, fixed day-of-month rank window) and
day-of-week (2026-09-03-018, fixed weekday-of-week identity): this one is
triggered by an irregular calendar GAP in the trading calendar itself
(holiday closures), not a fixed periodic rule.

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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
    min_gap_days: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long on any trading day whose gap (in calendar days) to the NEXT
    trading day present in the index is >= `min_gap_days` (default 3,
    matching the classic pre-3-day-weekend rule: Friday->Monday is a
    3-calendar-day gap, a holiday-adjacent Thursday->Monday gap is 4+).
    Flat on all other days. Since this looks at the *next* index date to
    decide today's position, it uses only information available intraday
    today (the trading calendar is known in advance -- unlike a
    price-derived signal, no look-ahead bias from future price data).
    """
    df = _prep(price_df)
    idx = df.index
    if len(idx) < 2:
        return pd.Series(0, index=idx)

    gap_days = idx.to_series().diff().shift(-1).dt.days
    gap_days = gap_days.fillna(0)
    position = (gap_days >= min_gap_days).astype(int)
    position.index = idx
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
