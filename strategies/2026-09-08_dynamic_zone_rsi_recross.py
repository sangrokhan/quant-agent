"""Strategy: Dynamic Zone RSI recross (Bollinger Bands applied to RSI itself).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-025):
Per https://www.quantifiedstrategies.com/dynamic-zone-rsi/, applying
Bollinger Bands (a rolling mean +/- std-dev multiplier) DIRECTLY to the
RSI series (not to price) produces adaptive overbought/oversold zones that
widen/narrow with the RSI's own recent volatility, instead of static 70/30
levels. The source's own signal rule is a RE-CROSS, not a simple threshold
touch: a bullish signal fires when RSI, having fallen below its own lower
Bollinger band (a dynamic oversold zone), crosses back ABOVE that lower
band -- confirming the oversold extreme has actually reversed rather than
just touching an arbitrary static level. Exit mirrors this: RSI crossing
back below its own dynamic upper band after having exceeded it, or a
max-hold-days time-stop for robustness (not in the original indicator,
added per repo convention for all new strategies).

This is distinct from all prior Bollinger+RSI combinations in this repo:
- TDI (2026-09-04-117) applies BB to RSI *moving averages* (fast/slow SMA
  of RSI), not to RSI directly, and its buy rule is a multi-line ordering
  condition, not a band recross.
- 2026-09-04-067 uses BB on PRICE plus a static RSI<30/>70 threshold as a
  confirmation filter -- two separate static/price indicators, not one
  adaptive band built from RSI's own distribution.
This strategy is the first to build the volatility band directly from the
RSI series itself.

Signal logic
------------
- RSI(rsi_window) computed via Wilder's smoothing (EMA-style) on daily
  closes.
- A `bb_window`-period SMA and STD of the RSI series form the "dynamic
  zone": upper = rsi_sma + bb_std * rsi_std, lower = rsi_sma - bb_std *
  rsi_std.
- Long entry: RSI was below `lower` at some point since the last flat
  state (has_touched_lower flag) and now crosses back above `lower`
  (recross-up confirmation, not mere touch).
- Exit: RSI crosses back below `upper` after having exceeded it while in
  position (mirrors bearish recross logic as a profit-take), OR a
  `max_hold_days` time-stop, whichever comes first.
- Flat otherwise. Long-only (no shorts), matching repo convention.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept the strategy's tunable parameters as keyword
arguments.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    # Wilder's smoothing (equivalent to an EMA with alpha=1/window).
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    bb_window: int = 20,
    bb_std: float = 1.8,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_window)
    rsi_sma = rsi.rolling(bb_window).mean()
    rsi_std = rsi.rolling(bb_window).std()
    upper = rsi_sma + bb_std * rsi_std
    lower = rsi_sma - bb_std * rsi_std

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    touched_lower = False  # since flat, has RSI dipped below `lower`?
    touched_upper = False  # while long, has RSI exceeded `upper`?

    valid = rsi.notna() & upper.notna() & lower.notna()

    for i in range(len(close)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue

        r = rsi.iloc[i]
        u = upper.iloc[i]
        l = lower.iloc[i]

        if in_position:
            if r > u:
                touched_upper = True
            held = i - entry_idx
            exit_recross = touched_upper and (r < u)
            if exit_recross or held >= max_hold_days:
                in_position = False
                touched_upper = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if r < l:
                touched_lower = True
            entry_recross = touched_lower and (r > l)
            if entry_recross:
                in_position = True
                entry_idx = i
                touched_lower = False
                touched_upper = False
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
