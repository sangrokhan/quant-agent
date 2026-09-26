"""Strategy: Bulkowski's "Trading Weinstein" Stage-2 setup with minor-low
trailing stop + wait-for-profit exit (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/TradingWeinstein.html (Thomas
Bulkowski's own detailed test of Stan Weinstein's Stage-2 method from
"Secrets for Profiting in Bull and Bear Markets"), read via browser_exec
-- web_extract's ddgs backend cannot fetch this domain. This is DISTINCT
from this repo's 3 prior generic Weinstein-Stage-2 entries (2026-09-10-127,
2026-09-10-128, 2026-09-18-124 -- all rejected/near-miss), which used a
simple "close below SMA" or "SMA slope flattens" exit. This entry instead
implements Bulkowski's own SPECIFIC stop-management + exit rules, which no
prior Weinstein entry in this repo has tested:

    "LOCATE the stop but don't place it yet. Use the lower of the value of
    the 30-week SMA below the closest minor low, or a penny below the
    closest minor low... If the SMA flattens out or turns down, raise the
    stop to the prior minor low (forget about putting it below the SMA).
    Tighten up the stop... Once the week's low is above the buy price, the
    position moves into a profit and we sell at the next bar's open."

Bulkowski's own disclosed stats (1/1/2000-1/1/2011 in-sample, out-of-sample
to 2023, 448/330 trades): avg gain 6%/5%, median gain 6%, win/loss ratio
74-75%, max loss -20%/-22%. Two genuinely novel mechanics vs prior Weinstein
entries in this repo: (1) the stop starts anchored below the nearest minor
swing low (not a fixed SMA-distance stop), only reverting to a plain
SMA-flatten exit once the SMA itself loses its rising slope, and (2) a
"wait for profit" exit gate -- once profitable, exit at the next bar's
open rather than holding for a bigger measured-move target, deliberately
sacrificing average gain for a higher win/loss ratio (Bulkowski's own
explicit trade-off).

Signal logic (numeric proxy for the source's qualitative rules, weekly
concepts scaled x5 to trading days per this repo's established convention
for weekly-designed Bulkowski setups)
------------------------------------------------------------------------
1. Entry: close breaks above the prior `resistance_window`-day rolling
   high (base/trendline-resistance breakout proxy) AND close > SMA(150)
   (30-week SMA proxy) AND the SMA has a POSITIVE slope over the last
   `slope_lookback` days (source: "the SMA must be rising").
2. Minor-low detection: a simple `pivot_window`-bar centered fractal low
   (a local low surrounded by higher lows on each side) supplies the
   "nearest minor low" the source's stop-placement rules reference.
3. Stop management: while in a trade, if the SMA slope remains positive,
   the active stop is the most recent confirmed minor low (source's own
   simplification: rather than modeling "SMA below the minor low", this
   repo tracks the tighter of the two automatically since a minor low in
   an uptrend generally sits above the concurrent SMA anyway). If the SMA
   slope turns non-positive, the stop switches to (and is henceforth only
   ever raised to) the most recent minor low regardless (source's own
   "tighten up the stop" instruction collapses to the same minor-low
   anchor in both regimes for this daily-bar approximation).
4. Wait-for-profit exit: once in a trade, if close > entry_price (position
   is profitable) AND today's low > entry_price (source: "once the week's
   low is above the buy price"), exit at the NEXT bar's open (approximated
   here as exiting the following bar).
5. Stop-loss exit: if close drops below the active stop level, exit
   immediately (source's stop-loss trigger).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _minor_lows(low: pd.Series, pivot_window: int) -> pd.Series:
    """Boolean series: True where `low` is a centered local minimum."""
    is_min = pd.Series(False, index=low.index)
    vals = low.values
    n = len(vals)
    for i in range(pivot_window, n - pivot_window):
        window = vals[i - pivot_window : i + pivot_window + 1]
        if vals[i] == window.min():
            is_min.iloc[i] = True
    return is_min


def generate_signals(
    price_df: pd.DataFrame,
    resistance_window: int = 50,
    sma_window: int = 150,
    slope_lookback: int = 10,
    pivot_window: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    sma = close.rolling(sma_window).mean()
    sma_slope_up = sma > sma.shift(slope_lookback)

    rolling_resistance = high.rolling(resistance_window).max().shift(1)
    entry = (close > rolling_resistance) & (close > sma) & sma_slope_up.fillna(False)
    entry = entry.fillna(False)

    minor_low_flag = _minor_lows(low, pivot_window)
    # last confirmed minor low value as of each bar (a minor low needs
    # `pivot_window` future bars to confirm, so shift by pivot_window to
    # avoid look-ahead: the confirmation is only known pivot_window bars
    # after the actual low bar).
    minor_low_value = low.where(minor_low_flag).ffill().shift(pivot_window)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_price = 0.0
    stop_level = 0.0
    pending_exit = False

    for i in range(len(close)):
        if in_position:
            if pending_exit:
                in_position = False
                position.iloc[i] = 0
                pending_exit = False
                continue

            mlv = minor_low_value.iloc[i]
            if pd.notna(mlv):
                stop_level = max(stop_level, mlv)

            if close.iloc[i] < stop_level:
                in_position = False
                position.iloc[i] = 0
                continue

            position.iloc[i] = 1
            if close.iloc[i] > entry_price and low.iloc[i] > entry_price:
                pending_exit = True
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_price = close.iloc[i]
                mlv = minor_low_value.iloc[i]
                stop_level = mlv if pd.notna(mlv) else close.iloc[i] * 0.85
                pending_exit = False
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    resistance_window: int = 50,
    sma_window: int = 150,
    slope_lookback: int = 10,
    pivot_window: int = 5,
) -> pd.Series:
    """Daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        resistance_window=resistance_window,
        sma_window=sma_window,
        slope_lookback=slope_lookback,
        pivot_window=pivot_window,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
