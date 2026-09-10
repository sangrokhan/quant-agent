"""Strategy: Weekly close-below-prior-week-low dip-buy, trend-gated, daily-momentum exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-042):
Per SetupAlpha's "I Tested 5 'Buy The Dip' Candle Patterns on SPY" (Jul 12
2026, visited this iteration --
https://setup4alpha.substack.com/p/tested-5-buy-the-dip-patterns-spy),
the source discloses the exact rule and standalone (unfiltered) backtest
numbers for "The Weekly Close Below Low" pattern: entry when
`Extern(~Weekly, c < l[1])` -- i.e. the CURRENT week's close is below the
PRIOR week's low (a sharper weekly-timeframe dip than any daily-bar
signal) -- exit on the simple daily momentum-flip rule `c > c[1]` (today's
close above yesterday's close). Source's own disclosed standalone
(no trend filter, no leverage) 2000-2026 SPY backtest: 64.13% win rate,
-31.56% max drawdown, 4.50% CAR, $228,975 net profit -- described by the
source as still "fundamentally weak" on a risk-adjusted basis (deep MDD
for mediocre CAR).

This is a genuinely new construction for this repo: the entry condition
is evaluated on WEEKLY-aggregated bars (comparing the week's close to the
PRIOR completed week's low, not a same-timeframe rolling N-day low as in
every previously-tested Donchian-breakdown/turtle-soup/failed-breakout
fade in this knowledge base), while the exit is a single-daily-bar
momentum flip. Since the source's own disclosed unfiltered version has a
weak risk-adjusted profile (deep 31.56% MDD for only 4.5% CAR), this
repo's adaptation tests whether adding a standard long-term uptrend gate
(close > SMA(trend_window)) -- the same "buy dips only within an uptrend"
filter this repo has successfully applied to other raw dip-buy signals
(e.g. DeMarker 2026-09-04-154, IBS variants) -- rescues the risk-adjusted
profile by avoiding dip-buys during structural downtrends (2008, 2022).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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
    trend_sma_window: int = 200,
    use_trend_filter: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: current week's close < the PRIOR completed week's low (weekly
    aggregation), evaluated and held from the first daily bar after that
    weekly close is known. Optionally gated by close > SMA(trend_sma_window)
    (long-term uptrend filter) when use_trend_filter=True.

    Exit: daily close > yesterday's close (source's own disclosed simple
    momentum-flip exit rule) -- position drops back to 0 the next bar.
    """
    df = _prep(price_df)
    close = df["close"]
    low = df["low"] if "low" in df.columns else close

    # Weekly aggregation: resample to weekly (Fri-anchored, pandas default
    # 'W' = week ending Sunday but only trading days present so effectively
    # last trading day of each week) close/low.
    weekly_close = close.resample("W").last()
    weekly_low = low.resample("W").min()
    prior_week_low = weekly_low.shift(1)

    weekly_dip_signal = (weekly_close < prior_week_low).astype(int)

    # Forward-fill the weekly dip decision onto the next trading days
    # until the following week's decision arrives (source's own semantics:
    # entry condition evaluated once per week, at the weekly close).
    daily_dip_flag = weekly_dip_signal.reindex(close.index, method="ffill").fillna(0).astype(int)

    trend_up = (close > close.rolling(trend_sma_window).mean()).astype(bool)

    # Exit trigger: daily close > yesterday's close (source's own rule).
    exit_trigger = (close > close.shift(1))

    # Build the position series via a simple state machine: enter on the
    # dip condition being newly true (only on days the weekly signal is
    # fresh, to avoid holding all week just because the flag stays set),
    # hold until the daily momentum-flip exit fires. Approximate "new
    # weekly signal only" via a rising edge on daily_dip_flag.
    dip_bool = daily_dip_flag.astype(bool)
    dip_rising_edge = dip_bool & (~dip_bool.shift(1).fillna(False))
    if use_trend_filter:
        entry_signal = dip_rising_edge & trend_up
    else:
        entry_signal = dip_rising_edge

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_trigger.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_position = True
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
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
