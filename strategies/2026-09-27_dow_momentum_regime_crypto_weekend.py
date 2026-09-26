"""Strategy: Day-of-week momentum with regime filter (Friday/Saturday
crypto weekend effect, momentum-confirmed, single-day hold).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-037):
Per Tigro Blanc's "Day-of-week momentum strategy for crypto" (Medium/
Coinmonks, https://medium.com/coinmonks/day-of-week-momentum-strategy-for-
crypto-with-308-annual-returns-and-sharpe-2-96-but-4bd4ef0a31a8, read via
browser_exec since web_extract's ddgs backend cannot extract page content):
across 5.7 years / 311 coins, Friday (+0.53%) and Saturday (+0.86%) show
statistically significant (p<0.001) positive mean daily returns in crypto.
The article's own strategy conditions entry on (a) the specific weekday,
(b) the PRIOR day's return being positive (momentum confirmation), and
(c) a crash-avoidance regime filter (trailing N-day BTC return not too
negative), holding for exactly one day. The source is notable for candidly
disclosing and fixing a look-ahead-bias bug in its own initial backtest
(reducing claimed Sharpe from 2.96 to a realistic 0.77) -- we implement the
CORRECTED (non-look-ahead) version here directly: all rolling stats use only
data strictly prior to the current bar's decision (shifted appropriately).
This differs from this repo's already-rejected unconditional crypto weekend
holds (2026-09-04-029, 2026-09-12-174) by requiring BOTH a momentum
confirmation AND a regime filter rather than trading the calendar effect
unconditionally, and from the Monday-avoidance variant (2026-09-22-069/070)
by targeting entry days (Fri/Sat) rather than an avoidance day.

Signal logic
------------
- entry_weekdays: which weekdays (0=Mon..6=Sun) are eligible entry days
  (default Friday=4, Saturday=5, matching the source's crypto finding;
  on equity daily bars only Friday exists as a trading day, so this
  naturally narrows on equities without needing a separate equity rule).
- Momentum confirmation: previous bar's return > 0.
- Regime filter: trailing `regime_window`-day return of the SAME price
  series (proxying "BTC 5-day return" for a single-asset backtest; note
  this is a same-asset regime proxy, not literally BTC for equity symbols)
  > regime_min_return (avoid entering during a sharp drawdown).
- Entry: eligible weekday AND momentum confirmed AND regime filter passes.
- Exit: always exit at the next bar's close (exactly 1-day hold), matching
  the source's rule.
- Long-only.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
    entry_weekdays: tuple = (4, 5),
    regime_window: int = 5,
    regime_min_return: float = -0.10,
) -> pd.Series:
    """Return a {0,1} long/flat position series (1-bar hold)."""
    df = _prep(price_df)
    close = df["close"]

    daily_ret = close.pct_change()
    prev_day_ret = daily_ret.shift(1)  # "yesterday's" return as of today's decision
    momentum_confirmed = prev_day_ret > 0

    # regime filter: trailing N-day return computed as of the PRIOR bar close
    # (strictly no look-ahead: uses close[t-1] vs close[t-1-regime_window])
    trailing_regime_ret = (close.shift(1) / close.shift(1 + regime_window)) - 1.0
    regime_ok = trailing_regime_ret > regime_min_return

    weekday = pd.Series(close.index, index=close.index).apply(
        lambda ts: ts.weekday() if hasattr(ts, "weekday") else pd.Timestamp(ts).weekday()
    )
    eligible_day = weekday.isin(list(entry_weekdays))

    entry = eligible_day & momentum_confirmed.fillna(False) & regime_ok.fillna(False)

    # exactly 1-bar hold: position on bar i is 1 iff entry signal fired on bar i
    position = entry.astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    entry_weekdays: tuple = (4, 5),
    regime_window: int = 5,
    regime_min_return: float = -0.10,
) -> pd.Series:
    """Return the strategy's daily return series (position-weighted, no costs).

    Position on bar i (decided using data available strictly before bar i's
    close) determines exposure to the return realized FROM bar i's close to
    bar i+1's close (i.e. entering at i's close, exiting at i+1's close) --
    equivalent to shifting the position forward by one bar relative to the
    return series it earns.
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        entry_weekdays=entry_weekdays,
        regime_window=regime_window,
        regime_min_return=regime_min_return,
    )
    daily_ret = close.pct_change().fillna(0.0)
    # position decided at bar i's close -> earns the return realized over [i, i+1]
    # i.e. daily_ret.shift(-1) at bar i, or equivalently strat_ret[i+1] = position[i]*daily_ret[i+1]
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
