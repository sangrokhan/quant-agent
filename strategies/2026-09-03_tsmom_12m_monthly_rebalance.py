"""Strategy: 12-month time-series (absolute) momentum, monthly rebalance,
with 200-day SMA trend filter, on equity indices and crypto.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-012):
Moskowitz/Ooi/Pedersen's "Time Series Momentum" (2012) academic result uses
a full trailing 12-month (252 trading day) return with NO skip-month
adjustment, and rebalances MONTHLY (not daily) -- both details differ from
every prior momentum attempt logged here (2026-09-03-002 used a 90d
lookback rebalanced daily; -003 used 45d + daily inverse-vol sizing; -004
swept 30-90d lookbacks ANDed with a 200d trend filter, still rebalanced
daily). The 004 near-miss failure mode was explicitly regime-dependent:
83% pass in low-vol cells vs only 4% in high-vol cells, consistent with a
daily-rebalanced signal whipsawing in choppy/high-vol periods. This
iteration tests whether (a) the longer, more standard 12-month lookback and
(b) reducing rebalance frequency to monthly (the signal is computed once
per month and held fixed for that month, cutting turnover/whipsaw
substantially) clears the MDD/Sharpe bar that the shorter-lookback,
daily-rebalanced variants narrowly missed.

Source: https://www.globalequitymomentum.com/articles/lookback-delay
(GEM/Antonacci-adjacent article) explicitly states Moskowitz/Ooi/Pedersen's
TSMOM academic foundation "uses the full trailing 12-month return with no
skip", and that GEM's own live signal checks monthly, not daily. This
motivates testing plain 12-month absolute momentum + monthly rebalance
(not the skip-month 12-1 variant, which the article argues is a
stock-level-only convention that doesn't transfer to index-level assets --
directly relevant since this repo trades index ETFs (QQQ/SPY) and
crypto majors (BTC/ETH), not individual stocks).

Novelty vs prior entries: distinct lookback length (252d vs 30-90d in
-002/-003/-004), distinct rebalance frequency (monthly vs daily in every
prior momentum entry), and grounded in a different, more specific source
than -004's (which cited a cross-sectional crypto momentum backtest, not
the academic TSMOM lookback/rebalance convention).

Signal logic
------------
- Trailing 252-trading-day (~12mo) return: r(t) = close[t] / close[t-252] - 1.
- 200-day SMA trend filter (AND-gate, same mechanism as -004/-008):
  close[t] > SMA_200[t].
- Long (position=1) iff r(t) > 0 AND close[t] > SMA_200[t]; flat otherwise.
- Signal evaluated once per calendar month (on the last trading day of the
  prior month) and held constant through the following month -- this is
  the "monthly rebalance" mechanic: position changes only at month
  boundaries, not every time the underlying daily signal flips.
- No shorting.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept the strategy's tunable parameters as kwargs.
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
    lookback_days: int = 252,
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series: 12m absolute momentum AND
    200d trend filter, evaluated monthly and held fixed within each month.
    """
    df = _prep(price_df)
    close = df["close"]

    trailing_return = close / close.shift(lookback_days) - 1.0
    trend_ok = close > close.rolling(trend_window).sum().div(trend_window) if trend_window > 0 else pd.Series(True, index=close.index)
    # (rolling mean via sum/window avoids importing extra deps; equivalent to close.rolling(w).mean())

    raw_daily_signal = (trailing_return > 0) & trend_ok
    raw_daily_signal = raw_daily_signal.fillna(False)

    if trend_window <= 0:
        # trend filter disabled: pure absolute-momentum signal
        raw_daily_signal = (trailing_return > 0).fillna(False)

    # Monthly rebalance: sample the raw daily signal on the LAST trading day
    # of each month, then forward-fill that decision through the following
    # month (shifted by one period so the decision made at month-end m is
    # applied starting month m+1 -- no look-ahead, and it naturally lines up
    # with the existing position.shift(1) convention in generate_returns
    # which shifts once more for daily trade-on-next-bar realism).
    month_end_signal = raw_daily_signal.resample("ME").last()
    # Reindex month-end decisions onto the daily index, holding each
    # decision constant for the following month (ffill onto daily grid).
    monthly_position = month_end_signal.reindex(
        pd.date_range(month_end_signal.index.min(), close.index.max(), freq="D")
    ).ffill()
    position = monthly_position.reindex(close.index, method="ffill").fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Shift by 1 day: yesterday's realized position determines today's
    # return exposure (avoid look-ahead / same-bar execution).
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
