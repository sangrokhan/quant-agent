"""Strategy: Williams VIX Fix Bollinger-Band spike oversold bounce.

Hypothesis (see knowledge_base/strategies_log.jsonl):
Larry Williams' VIX Fix (WVF) is a synthetic, options-free volatility/fear
proxy computed purely from OHLC price: WVF = 100 * (HighestClose(N) - Low)
/ HighestClose(N), measuring the percentage decline of the current low
below the highest close of the last N bars. Per pineify.app's Williams VIX
Fix explainer: "When the VIX Fix spikes above the upper Bollinger Band,
that's your 'everyone's panicking' signal... these tend to be the most
reliable" -- a spike of WVF above its own rolling Bollinger upper band (2
std) signals statistically extreme fear/panic-selling, historically
preceding a short-term bounce. Long entry on that spike; exit on WVF
reverting back below its own Bollinger midline (fear subsiding) or a
max_hold_days time-stop.

First Williams VIX Fix strategy in this repo -- distinct from all
volatility-regime filters already tested (Choppiness Index, Bollinger
Bandwidth squeeze, ATR-expansion breakout, VHF, Random Walk Index,
Historical Volatility Ratio) since WVF measures percentage price decline
from a recent high (a directional fear proxy), not a two-sided dispersion
measure -- structurally closer to a synthetic VIX than to any dispersion
statistic already tested.

Signal logic
------------
- WVF[t] = 100 * (max(close[t-N+1..t]) - low[t]) / max(close[t-N+1..t])
  (N = wvf_window, standard 22).
- Bollinger Bands (bb_window, bb_std) computed on WVF itself.
- Long entry: WVF crosses above its own upper Bollinger Band (spike =
  extreme fear).
- Exit: WVF crosses back below its own Bollinger midline (SMA), or a
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


def _williams_vix_fix(close: pd.Series, low: pd.Series, wvf_window: int) -> pd.Series:
    highest_close = close.rolling(wvf_window).max()
    wvf = 100 * (highest_close - low) / highest_close.replace(0, pd.NA)
    return wvf


def generate_signals(
    price_df: pd.DataFrame,
    wvf_window: int = 22,
    bb_window: int = 20,
    bb_std: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]

    wvf = _williams_vix_fix(close, low, wvf_window)
    wvf_mid = wvf.rolling(bb_window).mean()
    wvf_std = wvf.rolling(bb_window).std()
    wvf_upper = wvf_mid + bb_std * wvf_std

    long_trigger = (wvf > wvf_upper) & (wvf.shift(1) <= wvf_upper.shift(1))
    exit_trigger = (wvf < wvf_mid) & (wvf.shift(1) >= wvf_mid.shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger.iloc[i]) or held >= max_hold_days:
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
    wvf_window: int = 22,
    bb_window: int = 20,
    bb_std: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df, wvf_window=wvf_window, bb_window=bb_window,
        bb_std=bb_std, max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns
