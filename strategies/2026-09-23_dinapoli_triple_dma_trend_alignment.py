"""Strategy: DiNapoli 3x3 / 7x5 / 25x5 triple Displaced Moving Average
(DMA) trend alignment.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Joe DiNapoli's classic "Trading with DiNapoli Levels" methodology
(https://www.luxalgo.com/library/indicator/displaced-moving-average/ and
https://www.forexpeacearmy.com/forex-books/chapter/displaced-moving-average,
both read this iteration): DiNapoli popularized three forward-displaced
simple moving averages used TOGETHER as a multi-horizon trend filter --
DMA(3x3) = 3-period SMA shifted forward 3 bars (short-term trend),
DMA(7x5) = 7-period SMA shifted forward 5 bars (medium-term trend),
DMA(25x5) = 25-period SMA shifted forward 5 bars (long-term trend). This
repo already tested the single-DMA pullback-continuation construction
(2026-09-06-116, close touches/dips below one displaced MA and closes back
above it). This strategy is structurally different: it requires all THREE
displaced averages to align (a "stacked" bullish alignment,
close > DMA3x3 > DMA7x5 > DMA25x5) as a multi-timeframe trend CONFIRMATION
entry, exiting when the short-term DMA(3x3) loses alignment (close crosses
back below it) -- distinct from the single-line pullback-touch mechanic.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  (0/1 long/flat)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _displaced_sma(close: pd.Series, window: int, displacement: int) -> pd.Series:
    """Forward-displaced SMA: SMA(window) shifted forward `displacement`
    bars, i.e. the value plotted at bar t is the SMA computed as of bar
    t - displacement (a purely backward-looking / non-repainting shift,
    matching how a chart displays a "forward" shifted MA -- the value seen
    "now" at bar t was actually computed `displacement` bars ago).
    """
    sma = close.rolling(window, min_periods=window).mean()
    return sma.shift(displacement)


def generate_signals(
    price_df: pd.DataFrame,
    short_window: int = 3,
    short_disp: int = 3,
    med_window: int = 7,
    med_disp: int = 5,
    long_window: int = 25,
    long_disp: int = 5,
    max_hold_days: int = 30,
    vol_regime_gate: bool = False,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: close > DMA_short > DMA_med > DMA_long (full bullish
    triple-DMA stacked alignment, DiNapoli's multi-timeframe trend
    confirmation). Exit: close crosses back below DMA_short (loses the
    short-term trend reference), or a max_hold_days time-stop.

    vol_regime_gate: if True, only allow entries when the current
    `vol_window`-day realized volatility is <= `vol_regime_ratio` times its
    trailing `vol_lookback`-day median (low/mid-vol regime filter, same
    construction as strategies/2026-09-03_bb_meanrev_qqq_volregime.py) --
    direct rescue attempt for near-miss 2026-09-23-041, whose grid showed
    the edge concentrated in low/mid vol terciles (0/24 high-vol passes).
    """
    df = _prep(price_df)
    close = df["close"]

    dma_short = _displaced_sma(close, short_window, short_disp)
    dma_med = _displaced_sma(close, med_window, med_disp)
    dma_long = _displaced_sma(close, long_window, long_disp)

    stacked_bullish = (close > dma_short) & (dma_short > dma_med) & (dma_med > dma_long)
    exit_signal = close < dma_short

    if vol_regime_gate:
        log_ret = np.log(close / close.shift(1))
        realized_vol = log_ret.rolling(vol_window, min_periods=vol_window).std()
        trailing_median = realized_vol.rolling(vol_lookback, min_periods=max(20, vol_lookback // 4)).median()
        low_vol_regime = realized_vol <= (vol_regime_ratio * trailing_median)
        low_vol_regime = low_vol_regime.fillna(False)
        stacked_bullish = stacked_bullish & low_vol_regime
        exit_signal = exit_signal | (~low_vol_regime)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(stacked_bullish.iloc[i]):
                in_position = True
                entry_idx = i
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
