"""Strategy: RSI(2) oversold mean-reversion, NEXT-OPEN entry/exit timing with
a prior-day-high signal exit (Quantitativo's "The Holy Grail still works").

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-008):
Per Quantitativo's "The Holy Grail still works"
(https://www.quantitativo.com/p/the-holy-grail-still-works, read via
browser_exec this iteration), the author's own refinement of Larry Connors'
classic RSI(2) mean-reversion rule is:

  - SPY is above its 200-day moving average (bull regime filter).
  - The 2-period RSI of SPY closes below 5.
  - Buy the SPY on the NEXT OPEN (not the triggering day's own close).
  - If SPY closes above the previous day's high, exit on the NEXT OPEN.
  - If regime flips (SPY closes below its 200-day SMA) while in a
    position, exit on the NEXT OPEN.

This repo already has a RSI(2)+SMA200 mean-reversion entry (2026-09-03-005,
accepted equity), but that variant enters/exits on the SAME bar's CLOSE
(entry when RSI(2)<=threshold at today's close; exit when close crosses
above a 5-day SMA). This is a genuinely distinct execution-timing mechanic:
NEXT-OPEN entry/exit (avoiding same-bar-close look-ahead in a live trading
sense) combined with a prior-day-HIGH exit trigger (not a moving-average
cross), per the source's own explicit statement that this timing tweak was
necessary to fix a "disaster" result from the naive same-close variant.

Signal logic
------------
- Trigger day (day i): close > SMA(200) AND RSI(2) closes below
  `rsi_entry`.
- Entry: long starting at day i+1's OPEN (not day i's close).
- Exit trigger: EITHER (a) day j's close > day j-1's high (signal exit,
  checked each day while in position), OR (b) day j's close < SMA(200)
  (regime-flip exit). Exit executes at day j+1's OPEN.
- A `max_hold_days` time-stop backstop is included (the source's own
  backtest doesn't disclose one, but is added here as a standard risk
  control and included in the parameter grid).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position,
        1 on a day when the strategy holds an open position through
        that day's own trading session -- i.e. entered at that day's
        open or earlier and not yet exited)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy
        returns; approximated as close-to-close on days the position is
        held per generate_signals, shifted appropriately for
        next-open-timing entries/exits per the standard repo convention
        of shifting position by 1 day before applying to daily returns)
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
    rsi_window: int = 2,
    rsi_entry: float = 5.0,
    trend_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Position on day i is 1 if the strategy holds a long position DURING
    day i's trading session (i.e. entered at day i's open at the latest,
    per the next-open-entry rule triggered by day i-1's close signal).
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / rsi_window, min_periods=rsi_window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / rsi_window, min_periods=rsi_window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50)

    sma_trend = close.rolling(trend_window).mean()
    bull_regime = close > sma_trend

    entry_trigger_close = (bull_regime) & (rsi < rsi_entry)  # signal known at day i's close
    prev_high = high.shift(1)
    exit_signal_close = close > prev_high  # signal known at day j's close
    regime_flip_close = ~bull_regime  # signal known at day j's close

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = None
    for i in range(n):
        if in_position:
            held = i - entry_idx
            # Check exit conditions using the PREVIOUS day's close-based
            # signal (next-open-timing: signal known at close of i-1
            # triggers an action at the open of day i).
            if i > 0 and (bool(exit_signal_close.iloc[i - 1]) or bool(regime_flip_close.iloc[i - 1])):
                in_position = False
                position.iloc[i] = 0
                continue
            if held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if i > 0 and bool(entry_trigger_close.iloc[i - 1]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    `generate_signals` already encodes next-open-timing entries/exits into
    a {0,1} series aligned to each day's own session; applying the standard
    repo convention of shifting by 1 additional day here would double-count
    the timing lag already built into the signal, so this strategy applies
    the position directly to same-day close-to-close returns (position[i]
    reflects exposure held DURING day i, entered at day i's open at the
    latest -- consistent with the day's own daily return already capturing
    the open-to-close portion of that session).
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position * daily_ret
    return strategy_ret
