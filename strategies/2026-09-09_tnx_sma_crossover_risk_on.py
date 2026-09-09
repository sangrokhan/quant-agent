"""Strategy: 10-Year Treasury Yield (^TNX) crossing below its own N-day SMA
as a risk-on equity buy signal (intermarket falling-rates strategy).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-051):
Per QuantifiedStrategies.com's "19 Best Intermarket Strategies" (disclosed
via Google search snippet, visited this iteration): "When the ten-year
Treasury rate crosses below its 25-day moving average, we buy the S&P
500." The economic rationale (source's implicit framing, consistent with
standard intermarket-analysis logic): falling/declining long-term yields
typically reflect looser financial conditions and lower discount rates
for equity valuations, both risk-on tailwinds; the crossover captures the
START of a yield-decline regime rather than requiring an absolute yield
level threshold.

This differs mechanically from every prior yield-related entry in this
repo: 2026-09-05-024 (10Y-3M SPREAD un-inversion event, not the 10Y level
itself), 2026-09-10-041 (spread un-inversion + SMA trend filter combo).
This is a first simple-crossover-of-the-YIELD-ITSELF-vs-its-own-SMA
construction.

Signal logic
------------
- Requires an auxiliary `yield_df` kwarg: a pd.DataFrame with a
  DatetimeIndex and a `close` column (the ^TNX yield series), supplied by
  the caller pre-aligned/loadable via data/loaders.py's load_equity("^TNX",...).
- yield_sma = yield_df['close'].rolling(sma_window).mean()
- Entry (long, on the PRIMARY equity asset, e.g. SPY/QQQ): yield crosses
  below yield_sma (today yield<sma, yesterday yield>=sma).
- Exit: yield crosses back above yield_sma, or a max_hold_days time-stop.
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both require a `yield_df` kwarg (the ^TNX price series), pre-aligned to
price_df's asset by the caller.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _yield_signal_aligned(index: pd.DatetimeIndex, yield_df: pd.DataFrame, sma_window: int) -> tuple[pd.Series, pd.Series]:
    ydf = yield_df.copy()
    if "timestamp" in ydf.columns:
        ydf = ydf.set_index("timestamp")
    ydf = ydf.sort_index()

    target_index = index
    if getattr(target_index, "tz", None) is not None:
        target_index = target_index.tz_localize(None)
    if getattr(ydf.index, "tz", None) is not None:
        ydf.index = ydf.index.tz_localize(None)

    yld = ydf["close"].sort_index()
    yld_sma = yld.rolling(sma_window).mean()

    yld_aligned = yld.reindex(target_index.union(yld.index)).sort_index().ffill().reindex(target_index)
    sma_aligned = yld_sma.reindex(target_index.union(yld_sma.index)).sort_index().ffill().reindex(target_index)
    yld_aligned.index = index
    sma_aligned.index = index
    return yld_aligned, sma_aligned


def generate_signals(
    price_df: pd.DataFrame,
    yield_df: pd.DataFrame,
    sma_window: int = 25,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    yld, yld_sma = _yield_signal_aligned(df.index, yield_df, sma_window)

    cross_below = (yld < yld_sma) & ~(yld.shift(1) < yld_sma.shift(1)).fillna(False)
    cross_above = (yld > yld_sma) & ~(yld.shift(1) > yld_sma.shift(1)).fillna(False)

    n = len(df)
    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = bool(cross_above.iloc[i]) if pd.notna(cross_above.iloc[i]) else False
            if exit_now or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(cross_below.iloc[i]) if pd.notna(cross_below.iloc[i]) else False:
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
