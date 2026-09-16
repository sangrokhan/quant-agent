"""Strategy: Glitch Index mean-reversion (Active Trader magazine, Feb 2004).

Source: MQL5 CodeBase, Mladen Rakic's MT5 port of the "Glitch Index"
(https://www.mql5.com/en/code/20439, visited this iteration via browser_exec
-- web_search DDGS/Yahoo backend down with RequestError/TLS errors on every
query attempted this iteration), original source credited to Active Trader
magazine, February 2004. First Glitch Index entry in this repo (0 prior KB
hits).

Indicator formula (fully disclosed by the source, not reconstructed):

    SMA        = SMA(close, sma_period)              # default 30
    RocSMA     = ROC(SMA, 1) * 0.1 + 1                # 1-bar rate of change of the SMA, scaled
    SMAMult    = SMA * RocSMA
    Diff       = Close - SMAMult
    GlitchIndex = (Diff / Close) * 100

The system measures how far price has deviated from a "detrended" SMA
(the SMA adjusted by its own recent rate of change) as a percentage of
price, on the theory that price reverts to this detrended norm.

Trading rule (source's own exact stated rule, long-only per this repo's
SAFETY.md scope -- the source's own system is long-only too):
    Entry: GlitchIndex crosses below -entry_threshold (default -2) AND the
      highest GlitchIndex reading over the trailing lookback_bars (default
      30) is below +blowoff_ceiling (default +5) -- this "no-buy zone"
      condition explicitly prevents buying into a snap-back from an
      extreme overbought blow-off top, per the source's own stated
      rationale. Buy next bar at the market (operationalized here as
      entering on the signal bar's own close, consistent with this repo's
      other next-bar-signal conventions using position.shift(1) in
      generate_returns).
    Exit: GlitchIndex crosses above +exit_threshold (default +2). Sell
      next bar at the market.
    Source designed for daily/weekly timeframes -- this repo tests on
    daily bars, consistent with the source's own stated scope.

Interface contract (see validation/grid_test.py, validation/validators.py):
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


def _glitch_index(close: pd.Series, sma_period: int) -> pd.Series:
    sma = close.rolling(sma_period).mean()
    roc_sma = sma.pct_change(1) * 0.1 + 1.0
    sma_mult = sma * roc_sma
    diff = close - sma_mult
    return (diff / close) * 100.0


def generate_signals(
    price_df: pd.DataFrame,
    sma_period: int = 30,
    entry_threshold: float = -2.0,
    exit_threshold: float = 2.0,
    blowoff_ceiling: float = 5.0,
    lookback_bars: int = 30,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    gi = _glitch_index(close, sma_period)
    rolling_max_gi = gi.rolling(lookback_bars).max()

    raw_long_signal = (gi < entry_threshold) & (rolling_max_gi < blowoff_ceiling)
    raw_exit_signal = gi > exit_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(raw_exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(raw_long_signal.iloc[i]):
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
