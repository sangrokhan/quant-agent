"""Strategy: Bitcoin "Pi Cycle Top" macro-cycle-top exit signal.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per lookintobitcoin.com / bitbo.io / ryder.id (Google AI-overview synthesis
and multiple corroborating source pages, visited this iteration via
browser_exec fallback): the Pi Cycle Top Indicator uses two moving averages
of BTC's close price -- the 111-day MA (111DMA) and 2x the 350-day MA
(350DMA x2, so named because 350/111 ~ 3.153 ~ pi). When the faster 111DMA
crosses UP through the slower 350DMA x2, this has historically coincided
(within ~3 days) with Bitcoin's major bull-cycle price peaks (2013, 2017,
April 2021). The economic rationale: a sustained blow-off-top rally pushes
the short MA up fast enough to catch a doubled long MA, a pattern rare
enough historically to flag cycle-top euphoria.

Operationalized here as a long/flat trend-following overlay: hold BTC long
by default (or gated by its own SMA trend, via `trend_sma_window`), but go
FLAT whenever the Pi Cycle Top condition is active (111DMA > 350DMA*2) as a
risk-off macro-cycle-top circuit breaker, re-entering only after the
condition resolves (111DMA drops back below 350DMA*2) plus an optional
`reentry_buffer_days` cooldown to avoid whipsawing right at the crossover.

First Pi Cycle Top strategy in this repo -- distinct from all other
dual-SMA-crossover strategies (this is a MA-family confluence signal keyed
to a specific documented historical multi-year-cycle top pattern, not a
generic trend-crossover) and from the already-tested Bitcoin halving
500-day rule (2026-09-04-096, a pure calendar rule) and 4-year Presidential
Election Cycle (2026-09-08-163, a US-political calendar rule) -- this is the
first BTC-specific ON-CHAIN-MA-derived macro-cycle-timing signal.

Interface contract for validators (see validation/validators.py) /
grid_test.py (see validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

Note: 111/350-day MAs require ~350+ days of history before producing a
valid signal, and this repo's crypto loader (load_crypto) via ccxt
typically has enough daily history for BTC/ETH -- if the price_df is
hourly, the strategy resamples the moving-average calculation to daily bars
internally (using the last close of each UTC day) since the Pi Cycle Top
indicator is defined on daily bars.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _daily_close(df: pd.DataFrame) -> pd.Series:
    """Resample to one close price per UTC calendar day (last observation)."""
    hours = pd.Series(df.index).dt.hour
    if hours.nunique() > 1:
        daily = df["close"].groupby(df.index.normalize()).last()
        daily.index = pd.to_datetime(daily.index)
        return daily
    return df["close"]


def generate_signals(
    price_df: pd.DataFrame,
    short_ma_window: int = 111,
    long_ma_window: int = 350,
    long_ma_multiplier: float = 2.0,
    trend_sma_window: int = 0,
    reentry_buffer_days: int = 0,
) -> pd.Series:
    """Return a {0,1} long/flat position series aligned to price_df.index.

    Long by default (or gated by close>SMA(trend_sma_window) if
    trend_sma_window > 0), FLAT whenever the Pi Cycle Top condition
    (short_ma > long_ma * long_ma_multiplier) is active, with an optional
    reentry_buffer_days cooldown after the condition clears before resuming
    long exposure.
    """
    df = _prep(price_df)
    close = df["close"]
    daily_close = _daily_close(df)

    short_ma = daily_close.rolling(short_ma_window).mean()
    long_ma = daily_close.rolling(long_ma_window).mean()
    pi_cycle_top_active = short_ma > (long_ma * long_ma_multiplier)
    pi_cycle_top_active = pi_cycle_top_active.fillna(False)

    if reentry_buffer_days and reentry_buffer_days > 0:
        # Extend the "flat" window forward by reentry_buffer_days after the
        # condition clears, using a rolling max over the trailing window.
        pi_cycle_top_active = (
            pi_cycle_top_active.rolling(reentry_buffer_days + 1, min_periods=1).max().astype(bool)
        )

    # Reindex the daily risk-off flag back onto the original (possibly
    # hourly) index.
    risk_off = pi_cycle_top_active.reindex(close.index, method="ffill").fillna(False)

    if trend_sma_window and trend_sma_window > 0:
        trend_sma = close.rolling(trend_sma_window).mean()
        base_long = close > trend_sma
    else:
        base_long = pd.Series(True, index=close.index)

    position = (base_long & (~risk_off)).astype(int)
    return position.rename("position")


def generate_returns(
    price_df: pd.DataFrame,
    short_ma_window: int = 111,
    long_ma_window: int = 350,
    long_ma_multiplier: float = 2.0,
    trend_sma_window: int = 0,
    reentry_buffer_days: int = 0,
) -> pd.Series:
    """Position-weighted daily/hourly returns (no transaction costs),
    resampled to daily-compounded returns if the input is hourly (matches
    this repo's other hourly-bar crypto strategies)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        short_ma_window=short_ma_window,
        long_ma_window=long_ma_window,
        long_ma_multiplier=long_ma_multiplier,
        trend_sma_window=trend_sma_window,
        reentry_buffer_days=reentry_buffer_days,
    )
    bar_ret = close.pct_change().fillna(0.0)
    strat_bar_ret = bar_ret * position.shift(1).fillna(0)

    hours = pd.Series(df.index).dt.hour
    if hours.nunique() > 1:
        daily_ret = (1.0 + strat_bar_ret).groupby(df.index.normalize()).prod() - 1.0
        daily_ret.index = pd.to_datetime(daily_ret.index)
        return daily_ret.rename("returns")

    return strat_bar_ret.rename("returns")
