"""Strategy: Elder-Ray Index (Alexander Elder) Bull Power / Bear Power trend
confirmation, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per investopedia.com's "Elder-Ray Index: Overview, Formula, and
Limitations" page (visited this iteration via browser_exec, web_search
DDGS backend TLS-connection-errored on the query, several other candidate
sources 404'd), Alexander Elder's Elder-Ray Index derives Bull Power and
Bear Power from a 13-period EMA:
    Bull Power = Period High - 13-period EMA
    Bear Power = Period Low - 13-period EMA
Bull Power measures buyers' ability to push price above the EMA
"consensus value"; Bear Power measures sellers' ability to push price
below it. Investopedia's disclosed trading rule: "Technical traders should
consider long positions if the bull power is rising, bear power is in
negative territory and rising (getting weaker), and EMA is sloping
upward" -- i.e. a 3-part confirmation: EMA uptrend + Bear Power negative
but rising (bears losing conviction) + Bull Power rising (bulls gaining
conviction). Exit/short setup is the mirror image (EMA downtrend + Bull
Power positive but falling + Bear Power falling).

Distinct from every other momentum/trend strategy in this repo: uses TWO
SEPARATE derived series (high-minus-EMA and low-minus-EMA, not close-minus-
EMA) as independent bull/bear-conviction gauges, combined with an EMA-slope
trend filter -- a 3-way AND condition not replicated by any existing
oscillator-based or single-MA-slope strategy already tested. 0 prior
Elder-Ray/Bull-Bear-Power entries in this repo.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def generate_signals(
    price_df: pd.DataFrame,
    ema_period: int = 13,
    ema_slope_lookback: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry (Investopedia's disclosed 3-part confirmation, all true):
      1. EMA is sloping upward (EMA > EMA `ema_slope_lookback` bars ago).
      2. Bear Power is negative AND rising (less negative than
         `ema_slope_lookback` bars ago) -- bears losing conviction.
      3. Bull Power is rising (higher than `ema_slope_lookback` bars ago)
         -- bulls gaining conviction.
    Exit to flat: the mirror-image bearish confirmation (EMA sloping down,
    Bull Power positive and falling, Bear Power falling) OR the long
    condition simply no longer holds (revert to flat rather than short,
    since this is a long-only strategy per SAFETY.md scope).
    """
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    ema = close.ewm(span=ema_period, adjust=False).mean()
    bull_power = high - ema
    bear_power = low - ema

    ema_rising = ema > ema.shift(ema_slope_lookback)
    ema_falling = ema < ema.shift(ema_slope_lookback)

    bear_negative_rising = (bear_power < 0) & (bear_power > bear_power.shift(ema_slope_lookback))
    bull_rising = bull_power > bull_power.shift(ema_slope_lookback)

    bull_positive_falling = (bull_power > 0) & (bull_power < bull_power.shift(ema_slope_lookback))
    bear_falling = bear_power < bear_power.shift(ema_slope_lookback)

    long_signal = ema_rising & bear_negative_rising & bull_rising
    exit_signal = ema_falling & bull_positive_falling & bear_falling

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    state = 0
    long_vals = long_signal.fillna(False).values
    exit_vals = exit_signal.fillna(False).values

    for i in range(n):
        if bool(long_vals[i]):
            state = 1
        elif bool(exit_vals[i]):
            state = 0
        position.iloc[i] = state

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
