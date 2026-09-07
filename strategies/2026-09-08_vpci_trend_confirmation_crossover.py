"""Strategy: Volume Price Confirmation Indicator (VPCI) trend-confirmation
crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-030):
Per LazyBear's Volume Price Confirmation Indicator (VPCI), originally
published on TradingView in 2015 and documented with its exact formula
at https://pineify.app/pine-script/indicators/vpci:

    VPC = VWMA(close, long_term) - SMA(close, long_term)
    VPR = VWMA(close, short_term) / SMA(close, short_term)
    VM  = SMA(volume, short_term) / SMA(volume, long_term)
    VPCI = VPC * VPR * VM

"A positive number means price is above its volume-weighted average,
which is bullish... Multiply them together and you get the VPCI:
positive confirms bulls are in control, negative confirms bears."
Default periods per the source: short_term=5, long_term=20 (tuned for
daily charts).

This is a genuinely new indicator family for this repo -- distinct from
existing volume-price constructions (OBV, Klinger Volume Oscillator,
Chaikin Money Flow, Volume-Weighted MACD, PVO/PVT) because VPCI is the
PRODUCT of three separately-meaningful sub-components (a VWMA-vs-SMA
price-confirmation term, a short/long VWMA-vs-SMA ratio term, and a
short/long volume-ratio term) rather than a difference-of-two-moving-
averages or a cumulative running sum.

Signal logic
------------
- Compute VPCI per the formula above.
- Smooth with an SMA(vpci, ma_length) to reduce noise (source's own
  "optional moving average of the VPCI line" feature; default matches
  source's lengthMA=8).
- Long entry: smoothed VPCI crosses above zero (source: "positive
  confirms bulls are in control").
- Exit: smoothed VPCI crosses below zero (mirror bearish confirmation),
  or a max_hold_days time-stop (added for robustness, not in the source).
- Flat otherwise; long-only, matching repo convention.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py).
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


def _vwma(price: pd.Series, volume: pd.Series, window: int) -> pd.Series:
    pv = (price * volume).rolling(window).sum()
    v = volume.rolling(window).sum().replace(0, np.nan)
    return pv / v


def _vpci(df: pd.DataFrame, short_term: int, long_term: int, ma_length: int) -> pd.Series:
    close = df["close"]
    volume = df["volume"]

    vpc = _vwma(close, volume, long_term) - close.rolling(long_term).mean()
    vpr = _vwma(close, volume, short_term) / close.rolling(short_term).mean().replace(0, np.nan)
    vm = volume.rolling(short_term).mean() / volume.rolling(long_term).mean().replace(0, np.nan)

    vpci = vpc * vpr * vm
    vpci_smoothed = vpci.rolling(ma_length).mean()
    return vpci_smoothed


def generate_signals(
    price_df: pd.DataFrame,
    short_term: int = 5,
    long_term: int = 20,
    ma_length: int = 8,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    vpci = _vpci(df, short_term, long_term, ma_length)

    cross_up = (vpci > 0) & (vpci.shift(1) <= 0)
    cross_down = (vpci < 0) & (vpci.shift(1) >= 0)

    valid = vpci.notna()

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(df)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]):
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
