"""Strategy: Dormeier ADX + Trend Thrust Indicator (TTI) + Volume Price
Confirmation Indicator (VPCI) trend system.

Hypothesis (see knowledge_base id 2026-09-12-169):
Per TASC's August 2024 Traders' Tips implementation of Buff Pelz Dormeier's
"Volume Confirmation For A Trend System" article
(https://www.tradingview.com/script/K3s5dmdv-TASC-2024-08-Volume-Confirmation-For-A-Trend-System/,
full rule disclosure), a trend-following system combining three volume-
and-price indicators outperformed simpler ADX+MACD+OBV/VPCI-only variants
in the author's own research:

- **TTI** (Trend Thrust Indicator, a volume-weighted MACD variant):
  fast/slow VWMAs, volume multiple (VM) = (fast_VWMA/slow_VWMA)^2, then
  fast_VWMA is multiplied by VM and slow_VWMA divided by VM before
  differencing -> TTI. TTI's own rolling average is its signal line.
- **VPCI** (Volume Price Confirmation Indicator, Dormeier's own
  indicator): VPC = VWMA(long) - SMA(long); VPR = VWMA(short)/SMA(short);
  VM2 = VWMA(short)/VWMA(long); VPCI = VPC * VPR * VM2.
- **ADX** (Wilder's Average Directional Index, this repo's standard
  `_dmi_adx` helper, reused from 2026-09-03_adx_dmi_trend_filter.py).

Source's own disclosed entry/exit rule (applied here to a single symbol
instead of the source's S&P-500-constituent portfolio-screening version,
since this repo's data/loaders.py is single-symbol only):
  - Long entry: ADX > adx_threshold (source default 30) AND TTI crosses
    above its own signal line AND VPCI > 0 (volume confirms the trend).
  - Exit: VPCI crosses below 0 (volume contradicts the trend).

First Dormeier TTI/VPCI/ADX combined trend system in this repo -- distinct
from the already-tested standalone VPCI zero-cross (2026-09-08-030, no ADX
or TTI gate) and standalone ADX+DMI crossover (2026-09-03-*, no volume
component at all): here VPCI is a REQUIRED confirmation/exit gate on top
of a volume-weighted-MACD-style (TTI) trigger, matching the source's own
disclosed three-indicator combination.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(0.0, index=high.index)
    minus_dm = pd.Series(0.0, index=high.index)
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[(down_move > up_move) & (down_move > 0)]

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = _wilder_smooth(tr, period)
    plus_dm_smooth = _wilder_smooth(plus_dm, period)
    minus_dm_smooth = _wilder_smooth(minus_dm, period)

    plus_di = 100.0 * (plus_dm_smooth / atr.replace(0, pd.NA))
    minus_di = 100.0 * (minus_dm_smooth / atr.replace(0, pd.NA))

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    adx = _wilder_smooth(dx.fillna(0.0), period)
    return adx


def _vwma(price: pd.Series, volume: pd.Series, window: int) -> pd.Series:
    pv = (price * volume).rolling(window).sum()
    v = volume.rolling(window).sum()
    return pv / v.replace(0, pd.NA)


def _tti(close: pd.Series, volume: pd.Series, fast: int, slow: int, signal: int):
    fast_vwma = _vwma(close, volume, fast)
    slow_vwma = _vwma(close, volume, slow)
    vm = (fast_vwma / slow_vwma.replace(0, pd.NA)) ** 2
    adj_fast = fast_vwma * vm
    adj_slow = slow_vwma / vm.replace(0, pd.NA)
    tti = adj_fast - adj_slow
    tti_signal = tti.rolling(signal).mean()
    return tti, tti_signal


def _vpci(close: pd.Series, volume: pd.Series, short: int, long_: int) -> pd.Series:
    vwma_long = _vwma(close, volume, long_)
    sma_long = close.rolling(long_).mean()
    vpc = vwma_long - sma_long

    vwma_short = _vwma(close, volume, short)
    sma_short = close.rolling(short).mean()
    vpr = vwma_short / sma_short.replace(0, pd.NA)

    vm2 = vwma_short / vwma_long.replace(0, pd.NA)

    vpci = vpc * vpr * vm2
    return vpci


def generate_signals(
    price_df: pd.DataFrame,
    adx_period: int = 14,
    adx_threshold: float = 30.0,
    tti_fast: int = 5,
    tti_slow: int = 20,
    tti_signal: int = 9,
    vpci_short: int = 5,
    vpci_long: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]

    adx = _adx(high, low, close, adx_period)
    tti, tti_sig = _tti(close, volume, tti_fast, tti_slow, tti_signal)
    vpci = _vpci(close, volume, vpci_short, vpci_long)

    tti_cross_up = (tti > tti_sig) & (tti.shift(1) <= tti_sig.shift(1))
    entry = (adx > adx_threshold) & tti_cross_up & (vpci > 0)
    exit_signal = vpci < 0

    entry = entry.fillna(False)
    exit_signal = exit_signal.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    adx_period: int = 14,
    adx_threshold: float = 30.0,
    tti_fast: int = 5,
    tti_slow: int = 20,
    tti_signal: int = 9,
    vpci_short: int = 5,
    vpci_long: int = 20,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        adx_period=adx_period,
        adx_threshold=adx_threshold,
        tti_fast=tti_fast,
        tti_slow=tti_slow,
        tti_signal=tti_signal,
        vpci_short=vpci_short,
        vpci_long=vpci_long,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    return strat_returns
