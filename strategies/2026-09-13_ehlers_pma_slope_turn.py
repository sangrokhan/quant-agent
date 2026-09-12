"""Strategy: Ehlers Projected Moving Average (PMA) slope-turn trend following.

Source: John F. Ehlers, "Removing Moving Average Lag", TASC Traders' Tips,
March 2025 edition (EasyLanguage $PMA formula + WealthLab.com's own
"enter at market close when PMA(30) turns up, exit when it turns down"
strategy). Read via traders.com/Documentation/FEEDbk_docs/2025/03/TradersTips.html
(browser_exec this iteration -- web_search DDGS backend TLS-erroring on
every query attempted).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
A standard N-bar SMA lags price because it's centered on the middle of its
lookback window rather than the most recent bar. Ehlers' PMA removes this
lag by fitting a linear regression (OLS) over the trailing N bars and
PROJECTING the regression line forward to "now" using its own slope:
PMA = SMA + slope * (Length / 2). This shifts the regression's fitted
center-of-window value forward by half the window length, landing
approximately on the current bar -- a lag-corrected trend estimate,
architecturally distinct from every prior EMA/SMA/Ehlers-smoother-based
trend-following strategy in this repo (none use an explicit linear-
regression-slope-projected shift construction; the closest, the LRC
pullback strategy, uses the regression's raw current-bar fitted value with
no forward slope-projection, and the Kaufman Inside Channel strategy uses
max-deviation bands rather than a lag-shifted trend line).

Signal logic
------------
- length: OLS regression / SMA lookback window (source's own example: 20-30).
- For each bar, fit OLS: close ~ a + b*count over the trailing `length`
  bars (count = 1..length, oldest to newest, matching Ehlers' EasyLanguage
  indexing convention where Count=1 is the most recent completed prior
  bar... reproduced here via a standard trailing-window least-squares fit).
- slope = -(regression coefficient per Ehlers' own sign convention, i.e.
  positive slope means price rising over the window).
- SMA = mean of the window.
- PMA = SMA + slope * length / 2 (Ehlers' own projection formula).
- Entry (long): PMA turns UP (PMA[t] > PMA[t-1] AND PMA[t-1] <= PMA[t-2],
  a fresh slope-turn event, matching WealthLab's own "PMA(30) turns up"
  rule) -- optionally gated by a longer-term SMA trend filter
  (trend_window) to avoid counter-trend whipsaws, since this repo's
  established pattern shows unfiltered slope-turn strategies often fail on
  Sharpe/MDD without one.
- Exit: PMA turns DOWN (mirror condition) or trend filter breaks, or a
  max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
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


def _compute_pma(close: pd.Series, length: int) -> pd.Series:
    """Ehlers PMA: SMA + slope * length / 2, fit over trailing `length` bars."""
    n = len(close)
    pma = pd.Series(np.nan, index=close.index)
    values = close.values

    x = np.arange(1, length + 1)  # Count = 1..Length
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    for i in range(length - 1, n):
        # window oldest->newest: Ehlers' Price[Count-1] with Count=1..Length
        # means Price[0] (today) at Count=1, Price[Length-1] at Count=Length.
        # Reproduce by taking the trailing window and reversing it so index
        # 0 in `y` corresponds to Count=1 (most recent).
        window = values[i - length + 1 : i + 1][::-1]
        y = window
        y_mean = y.mean()
        sxy = ((x - x_mean) * (y - y_mean)).sum()
        slope = -sxy / x_var  # Ehlers' own sign convention (see EasyLanguage formula)
        sma = y_mean
        pma.iloc[i] = sma + slope * length / 2

    return pma


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 20,
    trend_window: int = 100,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    pma = _compute_pma(close, length)
    trend_sma = close.rolling(trend_window).mean()
    uptrend = (close > trend_sma).fillna(False)

    pma_prev1 = pma.shift(1)
    pma_prev2 = pma.shift(2)
    turn_up = (pma > pma_prev1) & (pma_prev1 <= pma_prev2)
    turn_down = (pma < pma_prev1) & (pma_prev1 >= pma_prev2)
    turn_up = turn_up.fillna(False)
    turn_down = turn_down.fillna(False)

    entry_cond = (turn_up & uptrend).fillna(False)
    exit_cond = (turn_down | (~uptrend)).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cond.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_cond.iloc[i]):
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
