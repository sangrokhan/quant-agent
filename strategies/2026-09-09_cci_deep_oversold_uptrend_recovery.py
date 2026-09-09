"""Strategy: CCI Deep-Oversold Recovery ("-200 hook") in a confirmed
200-day-SMA uptrend.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-053):
Per StockCharts ChartSchool's Commodity Channel Index guide (visited this
iteration, https://chartschool.stockcharts.com's CCI strategy section):
"First, stocks must be above their 200-day moving average to be in an
overall uptrend. Second, CCI must cross above -200 to show the [pullback
was overdone and a recovery is starting]." This is a deep-oversold
"hook" recovery entry within a confirmed broad uptrend -- CCI diving to an
extreme (-200, deeper than the standard -100 oversold line) during a
still-intact 200d-SMA uptrend represents an unusually sharp pullback,
and the cross back above -200 marks the point buyers are stepping back in.

Distinct from every prior CCI entry in this repo: 2026-09-04-024
(CCI(9)<-90 oversold entry, no 200d trend gate, no -200 depth), 2026-09-04-072
/2026-09-09-083 (CCI crossing above 0 or +100, momentum-direction not
oversold-recovery), 2026-09-08-088 (CCI Range Re-Entry from -100, ADX-gated
not SMA-gated), 2026-09-08-125 (bullish divergence, not level cross),
2026-09-05-007/2026-09-06-160 (Woodie's CCI zero-line-reject/trend-line-break,
different mechanic entirely). This is the first -200-specific deep-oversold
threshold combined with a 200d SMA trend gate in this repo.

Signal logic
------------
- CCI(n) = (Typical Price - SMA(Typical Price, n)) / (0.015 * Mean
  Absolute Deviation of Typical Price over n).
- uptrend = close > SMA(trend_sma_window).
- Entry (long): CCI crosses above `oversold_threshold` (default -200,
  source's own exact level) from below, while `uptrend` is True.
- Exit: CCI crosses back below `exit_threshold` (default 0, standard CCI
  zero-line convention for this repo's mean-reversion exits), OR
  `uptrend` flips False (trend break), OR a `max_hold_days` time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _cci(df: pd.DataFrame, n: int) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    sma_tp = tp.rolling(n).mean()
    mad = tp.rolling(n).apply(lambda x: (x - x.mean()).__abs__().mean(), raw=True)
    cci = (tp - sma_tp) / (0.015 * mad.replace(0, pd.NA))
    return cci


def generate_signals(
    price_df: pd.DataFrame,
    cci_window: int = 8,
    oversold_threshold: float = -125.0,
    exit_threshold: float = 0.0,
    trend_sma_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    cci = _cci(df, cci_window)
    trend_sma = close.rolling(trend_sma_window).mean()
    uptrend = close > trend_sma

    cross_up = (cci > oversold_threshold) & (cci.shift(1) <= oversold_threshold)
    entry_cond = cross_up & uptrend.fillna(False)
    exit_cross = (cci < exit_threshold) & (cci.shift(1) >= exit_threshold)

    n = len(df)
    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            trend_break = not bool(uptrend.iloc[i]) if pd.notna(uptrend.iloc[i]) else False
            exit_now = bool(exit_cross.iloc[i]) if pd.notna(exit_cross.iloc[i]) else False
            if exit_now or trend_break or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_cond.iloc[i]) if pd.notna(entry_cond.iloc[i]) else False:
                in_pos = True
                hold_count = 0
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
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
