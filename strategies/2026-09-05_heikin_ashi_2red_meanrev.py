"""Strategy: Heikin Ashi two-red-candle mean-reversion (contrarian).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-051):
Equity indices tend to mean-revert after a short burst of selling
pressure; QuantifiedStrategies.com's Heikin Ashi Trading Strategy article
(https://www.quantifiedstrategies.com/heikin-ashi-trading-strategy/)
backtests entering long at the close after `n_red_candles` (default 2)
consecutive red (bearish, close<open) Heikin Ashi candles, exiting on the
first day the RAW close trades above the prior day's RAW high (a
resumption-of-strength exit signal). This is the opposite (contrarian)
direction from the already-tested/rejected Heikin Ashi trend-following
variant (2026-09-04-045, N-consecutive-BULLISH HA candles + EMA filter,
long momentum continuation) -- here we buy exhaustion of a short
downswing, not confirmation of an upswing.

Signal logic
------------
- Heikin Ashi close_t = (O_t + H_t + L_t + C_t) / 4 (using RAW OHLC).
- Heikin Ashi open_t = (ha_open_{t-1} + ha_close_{t-1}) / 2, seeded with
  ha_open_0 = (O_0 + C_0) / 2.
- A HA candle is "red" (bearish) when ha_close_t < ha_open_t.
- Entry (long): the current bar completes the `n_red_candles`'th
  consecutive red HA candle (and we are currently flat) -- enter at that
  bar's close per the source's own backtest convention.
- Exit: RAW close_t > RAW high_{t-1} (source's own exit rule: "the exit is
  on a day when the close is higher than yesterday's high"), or a
  max_hold_days time-stop (source's rule alone can hold indefinitely in a
  stagnant/sideways market, so a backstop is added here).
- Flat (no position) at all other times.

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


def _heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    ha_close = (o + h + l + c) / 4.0

    ha_open = pd.Series(index=df.index, dtype=float)
    ha_open.iloc[0] = (o.iloc[0] + c.iloc[0]) / 2.0
    for i in range(1, len(df)):
        ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2.0

    return pd.DataFrame({"ha_open": ha_open, "ha_close": ha_close}, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    n_red_candles: int = 2,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    ha = _heikin_ashi(df)
    is_red = ha["ha_close"] < ha["ha_open"]

    consecutive_red = is_red.astype(int).groupby((~is_red).cumsum()).cumsum()
    entry_signal = consecutive_red == n_red_candles

    exit_signal = close > high.shift(1)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(len(df)):
        if pd.isna(high.shift(1).iloc[i]) or pd.isna(ha["ha_open"].iloc[i]):
            position.iloc[i] = 0
            continue
        if in_pos:
            hold_count += 1
            if bool(exit_signal.iloc[i]) or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
