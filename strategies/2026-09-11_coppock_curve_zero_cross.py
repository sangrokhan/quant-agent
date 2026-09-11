"""Strategy: Coppock Curve zero-line-cross long-only timing.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-121):
Source: https://www.quantifiedstrategies.com/coppock-curve-strategy/
E.S.C. Coppock's 1965 momentum indicator, originally computed on MONTHLY
bars as CoppockCurve = WMA(ROC(close, 11) + ROC(close, 14), 10), is a
long-term trend/momentum timing signal: go long when the curve crosses
above zero (a market bottom transitioning to an uptrend), exit when it
crosses back below zero. The source's own backtest (S&P 500, 1960-2023,
monthly bars) found only 12 trades in 63 years, a 100% win rate, and
meaningfully lower max drawdown than buy-and-hold (30.16% vs 52.56%) at
the cost of slightly lower absolute annual return (6.11% vs 7.03%), i.e.
a risk-reduction / drawdown-avoidance timing overlay rather than a
return-boosting strategy.

Adaptation for this repo's daily-bar data pipeline: rather than requiring
a separate monthly-resample data path, the classic 11/14/10 *month*
windows are converted to their trading-day equivalents (~21 trading days
per month): roc1_days=231 (11mo), roc2_days=294 (14mo), wma_days=210
(10mo). This keeps the same economic-cycle-length momentum smoothing
while operating directly on the daily price_df the validators expect.
This is a materially different indicator family from all prior ROC/MACD/
momentum-rank/trend-following entries in this repo -- no prior "Coppock"
hits in strategies_index.jsonl.

Signal logic
------------
- roc1 = pct change over roc1_days trading days (~11 months)
- roc2 = pct change over roc2_days trading days (~14 months)
- coppock = WMA(roc1 + roc2, wma_days) with linear weights 1..wma_days
- Entry (long): coppock crosses from <=0 to >0
- Exit (flat): coppock crosses from >0 to <=0
- Long-only, always either fully long or flat (no shorting) -- matches the
  source's own long-only, buy-and-hold-comparison framing.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = pd.Series(range(1, window + 1), dtype=float)

    def _apply(x):
        return (x * weights.values).sum() / weights.sum()

    return series.rolling(window).apply(_apply, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    roc1_days: int = 231,
    roc2_days: int = 294,
    wma_days: int = 210,
) -> pd.Series:
    """Return a {0,1} long/flat position series based on Coppock Curve zero-cross."""
    df = _prep(price_df)
    close = df["close"]

    roc1 = close.pct_change(roc1_days) * 100.0
    roc2 = close.pct_change(roc2_days) * 100.0
    coppock = _wma((roc1 + roc2).fillna(0.0).where((roc1.notna() & roc2.notna())), wma_days)

    above_zero = coppock > 0
    # cross-up = today above zero, yesterday not (or NaN treated as not-above)
    position = above_zero.fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Shift position by 1 day to avoid look-ahead bias.
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
