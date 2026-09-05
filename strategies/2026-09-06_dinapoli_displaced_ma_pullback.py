"""Strategy: DiNapoli Forward-Displaced Moving Average pullback continuation.

Hypothesis (see knowledge_base/strategies_log.jsonl):
Joe DiNapoli popularized forward-displaced simple moving averages (his
canonical 3x3, 7x5, 25x5 lines, "n x d" notation: n-period SMA shifted d
bars forward) as dynamic support/resistance references for trend
continuation. Per LuxAlgo's Displaced MA concept page
(https://www.luxalgo.com/library/concept/displaced-ma/): "As DiNapoli-style
dynamic support and resistance: in a trending market, pullbacks toward a
forward-displaced average are watched as continuation entries, and a close
through it is an early warning that the leg is maturing, not proof of
reversal." Because DMA(t) = SMA_n(t-d), the plotted line lags price and
"holds still while price pulls back to it in a trend" -- unlike a live MA,
it doesn't bend to the newest bars, so a pullback touch is a deliberately
stale (less noisy) reference level.

Operationalized here: in an established uptrend (close > SMA(trend_window)),
a pullback that touches or dips below the forward-displaced MA and then
closes back above it is a continuation-buy entry; exit on a close back
below the displaced MA (the source's own stated "early warning" signal) or
a max_hold_days time-stop.

First DiNapoli Displaced-MA strategy in this repo -- distinct from all
prior displaced/lagged average constructions (ZLEMA modifies the input
math to reduce lag; ordinary SMA/EMA crossovers use live, non-displaced
averages) since a genuinely forward-shifted plot is a novel mechanical
construction not tested elsewhere in this repo.

Signal logic
------------
- Trend filter: close > SMA(trend_window) (default 200).
- Displaced MA: DMA[t] = SMA(close, dma_window)[t - dma_displacement]
  (default dma_window=7, dma_displacement=5, i.e. DiNapoli's "7x5" line).
- Long entry: while in the uptrend regime, close crosses back above DMA
  after having dipped to/below it in the last `pullback_lookback` bars
  (pullback-and-recover pattern).
- Exit: close crosses below DMA, the trend filter breaks, or a
  max_hold_days time-stop.

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


def _displaced_ma(close: pd.Series, window: int, displacement: int) -> pd.Series:
    sma = close.rolling(window).mean()
    # Forward displacement: today's plotted DMA value is the SMA computed
    # `displacement` bars ago (a deliberately stale reference level).
    return sma.shift(displacement)


def generate_signals(
    price_df: pd.DataFrame,
    dma_window: int = 7,
    dma_displacement: int = 5,  # DiNapoli's canonical "7x5" line
    trend_window: int = 200,
    pullback_lookback: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    trend_ok = close > close.rolling(trend_window).mean()
    dma = _displaced_ma(close, dma_window, dma_displacement)

    touched_or_below = (close <= dma).rolling(pullback_lookback).max().astype(bool)
    recover_cross = (close > dma) & (close.shift(1) <= dma.shift(1))
    long_trigger = recover_cross & touched_or_below.shift(1).fillna(False) & trend_ok
    exit_trigger = (close < dma) & (close.shift(1) >= dma.shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger.iloc[i]) or not bool(trend_ok.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(long_trigger.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1

    position.name = "position"
    return position


def generate_returns(
    price_df: pd.DataFrame,
    dma_window: int = 7,
    dma_displacement: int = 5,
    trend_window: int = 200,
    pullback_lookback: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df, dma_window=dma_window, dma_displacement=dma_displacement,
        trend_window=trend_window, pullback_lookback=pullback_lookback,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns
