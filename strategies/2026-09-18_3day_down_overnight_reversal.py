"""Strategy: 3 Days Down Overnight Reversal (mean reversion, overnight-only hold).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-098):
Per quantifiedstrategies.com's "3 Days Down Overnight Trading Strategy"
(https://www.quantifiedstrategies.com/3-days-down-overnight-trading-strategy/):
after the index/ETF closes lower on 3 consecutive trading days, buy at the
close of the 3rd down day and exit at the next day's open (source's original
rule) or next day's close (source's disclosed variant, higher average gain
but bigger drawdown). Source reports (SPY, 1993-present, Amibroker backtest):
661 trades, 65% win rate, avg gain 0.13%/trade, max drawdown 8% for the
next-open exit; exit-at-next-close variant: avg gain 0.24%/trade, win rate
61%, max drawdown 17%. Source explicitly notes it "also works for Nasdaq 100
(QQQ) ... but not as well as for S&P 500" -- an honest scope note we
replicate in the grid test (equity SPY/QQQ + crypto for completeness).

First strategy in this repo using an *unconditional* N-consecutive-down-day
streak (no trend/oversold filter at all) with a strictly overnight-only
1-day hold, as opposed to:
 - 2026-09-04_mdd_multiple_days_down.py / 2026-09-08_connors_multiple_days_down_meanrev.py
   (Connors "N of last M days down" + 200d uptrend filter + 5d-SMA-recovery exit,
   no max hold, no overnight-only constraint),
 - 2026-09-18-093/-094 Lower-Highs/Lower-Lows (requires each day's HIGH also
   lower than the prior day's high, not just close-down).
This is the plain "3 consecutive closes down" version, unfiltered by any
long-term trend or short-term-mean condition, held for exactly 1 bar.

Signal logic
------------
- down_day[t] = close[t] < close[t-1]
- streak3[t] = down_day[t] & down_day[t-1] & down_day[t-2]  (3 consecutive down closes)
- Entry: at close[t] when streak3[t] is True.
- Exit: exactly `hold_days` bars later (default 1 -- i.e. exit at next day's
  close, matching source's higher-avg-gain "exit at close" variant; hold_days=1
  with an open-based approximation is not distinguishable in this repo's
  daily-close-to-close return convention, so `hold_days` controls how many
  bars the position is held before flattening, and `hold_days=1` reproduces
  the "hold one day" overnight-style trade with a daily return series).
- No trend filter, no stop-loss (matches source's simple rule). Long-only.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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
    down_streak: int = 3,
    hold_days: int = 1,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Enter long at the close of a bar completing `down_streak` consecutive
    down-closes; hold for exactly `hold_days` bars, then flatten.
    """
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    down_day = (close < close.shift(1)).astype(int)
    # streak count: True iff each of the last `down_streak` days was itself a down day
    streak_ok = down_day.rolling(down_streak).sum() >= down_streak

    position = pd.Series(0, index=close.index, dtype=int)
    hold_remaining = 0
    for i in range(n):
        if hold_remaining > 0:
            position.iloc[i] = 1
            hold_remaining -= 1
        else:
            if bool(streak_ok.iloc[i]):
                position.iloc[i] = 1
                hold_remaining = hold_days - 1
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
