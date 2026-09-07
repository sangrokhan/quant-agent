"""Strategy: Bill Williams' Market Facilitation Index (MFI/BW-MFI) "Squat" bar breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-095):
Per https://forex-indicators.net/bill-williams/mfi, the Market Facilitation
Index (MFI = (High-Low)/Volume, a measure of "market willingness to move
the price") is classified into 4 bar types by comparing MFI and Volume's
direction vs the prior bar. The "Squat" (Pink) bar -- MFI down/flat while
Volume rises -- is the source's own explicit standout: "the strongest
potential money maker of the 4 setups... many participants entering the
market... but before the battle between buyers and sellers finds a winner,
the price movement stops -- market sort of squats before leaping forward.
The breakout is going to be either seen as a reversal, or a continuation."
First Market Facilitation Index strategy in this repo -- distinct 4-quadrant
price-range/volume classification, not a moving-average or oscillator
smoothing construction like any prior volume-based strategy (OBV, CMF,
Force Index, EMV, Chaikin A/D, Klinger, Twiggs, VZO, Demand Index).

Concrete mechanical rule (operationalizing the source's qualitative
"leaping forward" breakout call, since the source doesn't give an exact
numeric backtest rule): after a confirmed Squat bar (MFI[t] <= MFI[t-1] AND
Volume[t] > Volume[t-1]), wait for price to break out of that squat bar's
own high/low range within `breakout_expiry_bars`; long entry on a
subsequent close above the squat bar's high, gated by close > SMA(trend_
window) (only take the continuation-direction breakout, consistent with
this repo's long-only convention and avoiding ambiguous reversal squats).

Signal logic
------------
- MFI = (High - Low) / Volume.
- Squat bar at t: MFI[t] <= MFI[t-1] AND Volume[t] > Volume[t-1].
- Entry (long): within breakout_expiry_bars after a squat bar, a close
  breaks above that squat bar's high AND close > SMA(trend_window).
- Exit: close crosses back below the squat bar's low, the trend filter
  breaks, or a max_hold_days time-stop.

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
    breakout_expiry_bars: int = 5,
    trend_sma_window: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    mfi = (high - low) / volume.replace(0, float("nan"))
    mfi = mfi.fillna(0.0)

    is_squat = (mfi <= mfi.shift(1)) & (volume > volume.shift(1))
    trend_sma = close.rolling(trend_sma_window).mean()
    trend_ok = close > trend_sma

    n = len(close)
    entry = pd.Series(False, index=close.index)
    squat_high_at_entry: dict = {}
    squat_low_at_entry: dict = {}

    squat_idx = [i for i in range(n) if bool(is_squat.iloc[i])]
    for si in squat_idx:
        squat_high = high.iloc[si]
        squat_low = low.iloc[si]
        expiry = min(si + breakout_expiry_bars, n - 1)
        for j in range(si + 1, expiry + 1):
            if close.iloc[j] > squat_high and bool(trend_ok.iloc[j]):
                entry.iloc[j] = True
                squat_high_at_entry[j] = squat_high
                squat_low_at_entry[j] = squat_low
                break

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_squat_low = None
    for i in range(n):
        if in_position:
            held = i - entry_idx
            failed = entry_squat_low is not None and close.iloc[i] < entry_squat_low
            trend_break = not bool(trend_ok.iloc[i])
            if failed or trend_break or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                entry_squat_low = squat_low_at_entry.get(i)
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
