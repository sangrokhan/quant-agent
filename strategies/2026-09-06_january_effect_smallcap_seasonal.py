"""Strategy: January Effect small-cap seasonal long (IWM-style calendar anomaly).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-133):
Per QuantPedia's "January Effect in Stocks" strategy page (citing Keim
1983 and the tax-loss-selling hypothesis): small-cap stocks have
historically shown unusually strong January returns, attributed to
investors selling losers in December for tax purposes then reinvesting in
January. QuantPedia's own page candidly notes the effect has weakened and
"transaction costs make it impossible to trade this anomaly" in the
recent period -- this strategy operationalizes the anomaly as literally as
possible (long a small-cap-tilted instrument for the calendar month of
January only, flat otherwise) specifically to test that decay claim
empirically on this repo's available instruments, rather than assuming it
still holds. Genuinely new calendar effect in this repo (distinct from the
already-tested Santa Claus Rally (~7 trading days spanning year-end/New
Year) and Halloween/Sell-in-May (6-month hold) -- this is a full-month,
January-specific window, and explicitly targets the small-cap risk premium
rationale rather than a pure liquidity/rally-around-holiday rationale).

Signal logic
------------
- Long-only, in position on every trading day whose calendar month == 1
  (January), flat every other month.
- No indicator computation needed -- pure calendar rule, per the source.
- Optional early-January-only variant via `end_day` (Keim's original
  finding was concentrated in the first ~5 trading days of January) is
  exposed as a parameter for the grid to test both the "full month" and
  "first N trading days only" variants.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series {0,1} long/flat
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
    end_trading_day: int = 21,  # 21 ~= all of January's trading days; smaller = early-Jan-only variant
) -> pd.Series:
    """Return a {0,1} long/flat position series. Long during January's
    first `end_trading_day` trading days each year, flat otherwise."""
    df = _prep(price_df)
    idx = df.index

    is_january = pd.Series(idx.month == 1, index=idx)
    # Rank each January trading day within its own year (1-indexed).
    years = pd.Series(idx.year, index=idx)
    jan_day_rank = pd.Series(0, index=idx, dtype=int)
    for yr, grp_idx in pd.Series(idx, index=idx).groupby(years).groups.items():
        jan_mask_yr = is_january.loc[grp_idx]
        jan_idx = grp_idx[jan_mask_yr.values]
        for rank, ts in enumerate(sorted(jan_idx), start=1):
            jan_day_rank.loc[ts] = rank

    pos = ((is_january) & (jan_day_rank >= 1) & (jan_day_rank <= end_trading_day)).astype(int)
    return pos


def generate_returns(
    price_df: pd.DataFrame,
    end_trading_day: int = 21,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(price_df, end_trading_day=end_trading_day)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret
