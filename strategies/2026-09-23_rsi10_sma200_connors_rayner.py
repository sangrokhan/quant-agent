"""Strategy: RSI(10) oversold mean-reversion, 200-day SMA trend gate,
next-day-open entry, dual exit (RSI recovery or time-stop).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-XXX):
Per TradingWithRayner's "Mean Reversion Trading Strategy That Works
(86.84% Winning Rate)"
(https://www.tradingwithrayner.com/mean-reversion-trading-strategy/, read
via browser_exec this iteration -- web_search DDGS/Yahoo backend
TLS-errored on every query attempted, citing Larry Connors & Cesar
Alvarez's original methodology): (1) close > SMA(200) confirms a long-term
uptrend regime; (2) RSI(10) < 30 identifies a short-term oversold pullback
within that uptrend; (3) buy at the NEXT DAY'S OPEN (not the signal day's
close, since RSI(10) can only be confirmed once the bar closes); (4) exit
when RSI(10) crosses above 40 (mean-reversion target reached) OR after 10
trading days (time-stop), whichever comes first.

This specific parameter combination (RSI period=10, entry threshold=30,
exit threshold=40, next-day-OPEN entry rather than same-day close) is
distinct from prior RSI mean-reversion constructions already tested in
this repo: 2026-09-03-005 (RSI(2), SMA(5)-recovery exit, same-day-close
entry) and 2026-09-10-083 (RSI(4), fixed exit=55, same-day-close entry).
The next-day-open entry (rather than same-day-close) is itself a distinct
execution-timing choice worth testing for its own transaction-cost/timing
implications, on top of the different RSI period/threshold combo.

Signal logic
------------
- Trend gate: close > SMA(sma_window).
- Entry trigger (signal day t): RSI(rsi_window) < rsi_entry AND trend gate
  true on day t. Position becomes active starting day t+1 (approximating
  "buy at next day's open" -- this repo's generate_returns already applies
  a 1-day shift for every strategy to avoid look-ahead, so the signal-day
  position flag maps naturally onto a next-day entry once shifted).
- Exit: RSI(rsi_window) crosses above rsi_exit, OR held >= max_hold_days,
  OR the trend gate breaks (close falls below SMA(sma_window)).

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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 200,
    rsi_window: int = 10,
    rsi_entry: float = 30.0,
    rsi_exit: float = 40.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(sma_window).mean()
    trend_up = close > sma

    rsi = _rsi(close, rsi_window)
    entry = (rsi < rsi_entry) & trend_up.fillna(False)
    exit_rsi = rsi > rsi_exit
    exit_trend_break = ~trend_up.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_rsi.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    NOTE on entry timing: this repo's convention (position.shift(1) applied
    below, identical to every other strategy file) already means the
    signal computed on day t's CLOSE only starts contributing to returns
    from day t+1 onward -- this naturally approximates the source's own
    "buy at next day's open" rule (the alternative of trading at day t's
    own close would require look-ahead, since RSI(10)<30 can only be
    confirmed once day t's bar is complete).
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
