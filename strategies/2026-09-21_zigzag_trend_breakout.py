"""Strategy: Percent-deviation ZigZag confirmed-pivot trend-continuation breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-268):
Per FXGlory's "Forex ZigZag Strategy: 5 Confirmed-Pivot Setups Backtested"
(https://fxglory.com/learn/forex-strategies/forex-zigzag-strategy/), a
percent-deviation ZigZag indicator (a proxy for MT4/MT5/TradingView ZigZag,
using a fixed percent-threshold swing confirmation instead of Depth/
Deviation/Backstep) can be used, WITHOUT lookahead bias, to define confirmed
swing highs/lows and trade breakouts beyond the most recent confirmed
opposite-direction swing in the direction of confirmed higher-high/
higher-low (or lower-high/lower-low) structure. The source's own backtest
(1H forex, 6 major pairs) found this was the LEAST-BAD of 5 tested ZigZag
setups (-0.0542R expectancy, still net negative) but that test used 1H FX
bars with tight spread/slippage costs baked in. This is the first ZigZag
strategy tested in this repo (0 prior KB hits for "Zig Zag") -- testing
whether the same confirmed-pivot breakout construction behaves differently
on DAILY equity/crypto bars (different timeframe/asset class/cost profile
than the source's negative 1H-forex result).

Signal logic
------------
- ZigZag pivots: walk forward tracking running high/low since the last
  confirmed pivot; a new opposite-direction pivot is CONFIRMED once price
  reverses by >= `deviation_pct` from the running extreme. The most recent
  (potentially still-forming) leg is never used for a signal -- only
  confirmed pivots, avoiding the repainting/lookahead problem the source
  flags.
- Structure: track the last two confirmed swing highs and the last two
  confirmed swing lows. Up-structure = latest confirmed swing low > the
  swing low before it (higher low) AND latest confirmed swing high > the
  swing high before it (higher high).
- Entry (long): in confirmed up-structure, close breaks above the most
  recent confirmed swing high (trend-continuation breakout, setup #1 from
  the source, its least-bad setup).
- Exit: close breaks below the most recent confirmed swing low (structure
  invalidation, source's own "stop beyond the most recent confirmed
  opposite swing" idea, translated from a fixed-R stop to a structural
  stop since we trade a continuous position series not per-trade R), OR a
  `max_hold_days` time-stop (this repo's standard fallback exit, since the
  source's fixed-R target isn't directly expressible in a position series).
- Flat otherwise.

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


def _confirmed_zigzag_pivots(close: pd.Series, deviation_pct: float) -> pd.DataFrame:
    """Walk-forward percent-deviation ZigZag. Returns a DataFrame aligned to
    close.index with columns:
      - last_high: value of the most recently CONFIRMED swing high as of
        this bar (NaN until the first pivot confirms)
      - last_low: value of the most recently CONFIRMED swing low
      - prev_high: the confirmed swing high before last_high
      - prev_low: the confirmed swing low before last_low
    All values are shifted so that at bar t they reflect only information
    confirmed strictly before/at bar t (no lookahead -- the final forming
    leg is never surfaced until it actually confirms).
    """
    n = len(close)
    vals = close.values
    last_high = [float("nan")] * n
    last_low = [float("nan")] * n
    prev_high = [float("nan")] * n
    prev_low = [float("nan")] * n

    confirmed_highs: list[float] = []
    confirmed_lows: list[float] = []

    # direction: 1 = looking for a high (currently in an up-leg), -1 = looking for a low
    direction = 0
    extreme_val = vals[0]
    extreme_idx = 0

    for i in range(n):
        price = vals[i]
        if direction == 0:
            # bootstrap: establish initial direction from first deviation
            if price >= extreme_val * (1 + deviation_pct):
                direction = 1
                extreme_val = price
                extreme_idx = i
            elif price <= extreme_val * (1 - deviation_pct):
                direction = -1
                extreme_val = price
                extreme_idx = i
            else:
                if price > extreme_val:
                    extreme_val = price
                    extreme_idx = i
                elif price < extreme_val:
                    pass
        elif direction == 1:
            if price > extreme_val:
                extreme_val = price
                extreme_idx = i
            elif price <= extreme_val * (1 - deviation_pct):
                # confirm the swing high at extreme_idx
                confirmed_highs.append(extreme_val)
                direction = -1
                extreme_val = price
                extreme_idx = i
        elif direction == -1:
            if price < extreme_val:
                extreme_val = price
                extreme_idx = i
            elif price >= extreme_val * (1 + deviation_pct):
                confirmed_lows.append(extreme_val)
                direction = 1
                extreme_val = price
                extreme_idx = i

        # record state AS OF this bar (only what's already confirmed)
        if confirmed_highs:
            last_high[i] = confirmed_highs[-1]
        if len(confirmed_highs) >= 2:
            prev_high[i] = confirmed_highs[-2]
        if confirmed_lows:
            last_low[i] = confirmed_lows[-1]
        if len(confirmed_lows) >= 2:
            prev_low[i] = confirmed_lows[-2]

    return pd.DataFrame(
        {
            "last_high": last_high,
            "last_low": last_low,
            "prev_high": prev_high,
            "prev_low": prev_low,
        },
        index=close.index,
    )


def generate_signals(
    price_df: pd.DataFrame,
    deviation_pct: float = 0.05,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    piv = _confirmed_zigzag_pivots(close, deviation_pct)

    up_structure = (piv["last_low"] > piv["prev_low"]) & (piv["last_high"] > piv["prev_high"])
    breakout_entry = up_structure & (close > piv["last_high"])
    structure_stop = close < piv["last_low"]

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    hold_bars = 0
    for i in range(len(close)):
        if in_pos:
            hold_bars += 1
            if bool(structure_stop.iloc[i]) or hold_bars >= max_hold_days:
                in_pos = False
                hold_bars = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(breakout_entry.iloc[i]):
                in_pos = True
                hold_bars = 0
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    deviation_pct: float = 0.05,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, deviation_pct=deviation_pct, max_hold_days=max_hold_days)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
