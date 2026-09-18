"""Strategy: 3-Day RSI Oversold Bounce, signal-based exit (close > yesterday's high).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-095):
Per quantifiedstrategies.com's "What Happens When Stock Markets Are
Oversold?" article
(https://www.quantifiedstrategies.com/what-happens-when-stock-markets-are-oversold/):
when a 3-day RSI drops below a low threshold (source uses 20), the market
has fallen significantly over the last 3 days and is oversold; enter at
the close. Source's own disclosed EXIT rule is distinctive: "we... wait
until the market gets a solid up day in the opposite direction and closes
above yesterday's high" -- i.e. a signal-based exit (close crossing above
the PRIOR day's high, not a same-day reversal or RSI-recovery exit), not
a fixed N-day time-stop. Source's SPY backtest since 1985: 484 trades,
avg gain 0.64%/trade, win rate 75%, CAGR 7.7%, MDD 26%, profit factor 2.5.
Distinct from every other RSI/Connors-RSI-family entry in this repo
(2026-09-04-xxx family, RMI 2026-09-05-013, QS RSI 2026-09-04-164) since
all of those use either an RSI-recovery-threshold exit or a fixed
time-stop -- this is the only entry using a "close > yesterday's high"
signal exit combined with a plain 3-day RSI oversold entry, with a
time-stop only as a backstop safety net (not the primary exit).

Signal logic
------------
- 3-day RSI (Wilder's RSI, period=3) < rsi_oversold (default 20) ->
  enter at close.
- Exit: close crosses above the PRIOR day's high (source's own disclosed
  signal-based exit), OR a max_hold_days time-stop backstop (this repo's
  established safety-net pattern for otherwise open-ended signal exits).
- Flat otherwise; long-only, no re-entry while already in a position.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 3,
    rsi_oversold: float = 20.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    rsi = _rsi(close, rsi_period)
    entry_condition = (rsi < rsi_oversold).fillna(False)
    high_prev = high.shift(1)
    exit_condition = (close > high_prev).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_condition.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_condition.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    ``leverage_cap`` (default 1.0) scales notional exposure, following this
    repo's established leverage-cap pattern for crypto max-drawdown control.
    """
    leverage_cap = kwargs.pop("leverage_cap", 1.0)
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret * leverage_cap
    return strategy_ret
