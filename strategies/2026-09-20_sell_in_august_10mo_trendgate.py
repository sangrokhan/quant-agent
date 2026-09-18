"""Strategy: "Sell in August and Go Away" 10-month seasonality + 200-day
SMA trend-eligibility gate (rescue attempt for near-miss id
2026-09-20-003).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-004):
Direct fix for this same cron trigger's prior rejection 2026-09-20-003
(unconditional 10-month "Sell in August" calendar hold, per
https://alvarezquanttrading.com/blog/sell-in-august-and-go-away/):
QQQ cleared the Sharpe threshold (1.116) but failed max-drawdown (0.328
vs 0.25) because the unconditional entry captured the full 2022
bear-market drawdown with no risk control. This sub-iteration adds this
repo's standard trend-eligibility gate (identical construction to the
already-accepted 2026-09-18-140 FabTrader ETF Rotation and other
trend-gated strategies in this repo): only take the seasonal entry if
close > SMA(trend_window) at the entry date; if the trend filter fails
at entry time, skip that year's seasonal window entirely (stay flat) --
the underlying calendar hold logic (entry_month/hold_months) and
scheduled exit are otherwise UNCHANGED from 2026-09-20-003's own
mechanics, so this isolates the trend-filter's effect on the specific
MDD failure.

Interface contract for validators (see validation/validators.py) and
grid_test.py: both generate_signals and generate_returns accept all
tunable parameters as keyword arguments.
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
    entry_month: int = 10,
    hold_months: int = 10,
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Same 10-month seasonal window as the ungated version
    (2026-09-20_sell_in_august_10mo_seasonality.py), but the entry only
    fires if close > SMA(trend_window) on the scheduled entry date;
    otherwise that year's window is skipped (stay flat through the whole
    would-be holding period).
    """
    df = _prep(price_df)
    close = df["close"]
    idx = close.index
    sma_trend = close.rolling(trend_window).mean()

    month_period = idx.to_period("M")
    next_month_period = pd.Series(month_period).shift(-1)
    is_month_end = (pd.Series(month_period, index=idx) != next_month_period.values)
    is_month_end.iloc[-1] = True

    months = pd.Series(idx.month, index=idx)
    trend_ok = (close > sma_trend).fillna(False)

    position = pd.Series(0, index=idx, dtype=int)
    in_position = False
    exit_target_period = None

    for i in range(len(idx)):
        cur_period = month_period[i]
        if in_position:
            if is_month_end.iloc[i] and cur_period == exit_target_period:
                position.iloc[i] = 1
                in_position = False
            else:
                position.iloc[i] = 1
        else:
            if is_month_end.iloc[i] and months.iloc[i] == entry_month:
                if bool(trend_ok.iloc[i]):
                    in_position = True
                    position.iloc[i] = 1
                    exit_target_period = cur_period + hold_months
                # else: trend filter fails, skip this year's window entirely
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
