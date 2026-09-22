"""Strategy: Reverse Elder Impulse System, Neutral-transition trigger (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-071):
Per Tradinformed's "How to Trade the S&P500 Using The Impulse Indicator"
(https://www.tradinformed.com/how-to-trade-the-sp500-using-the-impulse-indicator/,
read via browser_exec this iteration -- web_search's DDGS backend intermittently
TLS-erroring/no-results on several queries this iteration), the SOURCE'S OWN
disclosed rule set is: standard Impulse System enters long when the Impulse
Indicator (13-EMA slope + MACD-Histogram slope both classifying bull/bear/
neutral) turns Positive from a prior Neutral state, exits when it returns to
Neutral. The source's 20-year SPY backtest (1996-2016) found this STANDARD
rule lost money (net -$81,551, profit factor 0.73, 36% win rate, 85% max
drawdown) -- but REVERSING the signal (long when Impulse turns Negative from
Neutral, i.e. a contrarian/mean-reverting read of a momentum indicator) was
dramatically profitable in their own backtest (net +$350,922, profit factor
1.6, 64% win rate, 20% max drawdown). This repo has 3 prior Elder Impulse
entries (2026-09-04-064 green-bar-long, 2026-09-04-125 HTF-filtered variant,
2026-09-14-133 continuous-sizing dial) -- all use the STANDARD (bullish=long)
direction and a persistent-state color-classification trigger. This is the
first REVERSED-direction Elder Impulse test in this repo, and it uses a
distinct NEUTRAL-TRANSITION trigger (enter only on the specific Neutral->
Negative transition bar, not "any bar currently red") per the source's exact
disclosed rule, rather than the repo's existing green/red persistent-state
convention.

Entry: prior bar impulse state == Neutral AND current bar impulse state ==
Negative (bearish impulse: EMA falling AND MACD histogram falling) -> go
long (contrarian read).
Exit: current bar impulse state == Neutral.
Optional close>SMA(trend_window) gate (off by default, trend_window=0 means
no filter) to test whether an uptrend filter can control the drawdown risk
this contrarian construction otherwise carries.

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


def _macd_histogram(close: pd.Series, fast: int, slow: int, signal: int) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line - signal_line


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 13,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    trend_window: int = 0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema = close.ewm(span=ema_window, adjust=False).mean()
    hist = _macd_histogram(close, macd_fast, macd_slow, macd_signal)

    ema_rising = ema > ema.shift(1)
    hist_rising = hist > hist.shift(1)
    ema_falling = ema < ema.shift(1)
    hist_falling = hist < hist.shift(1)

    green = ema_rising & hist_rising  # bullish impulse
    red = ema_falling & hist_falling  # bearish impulse
    # state: 1=green(positive), -1=red(negative), 0=neutral(blue)
    state = pd.Series(0, index=df.index, dtype=int)
    state[green] = 1
    state[red] = -1

    prev_state = state.shift(1).fillna(0)

    if trend_window and trend_window > 0:
        sma = close.rolling(trend_window).mean()
        uptrend = close > sma
    else:
        uptrend = pd.Series(True, index=df.index)

    # Entry trigger: Neutral -> Negative transition (reversed/contrarian long)
    entry_trigger = (prev_state == 0) & (state == -1) & uptrend

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        if in_position:
            if state.iloc[i] == 0:  # returned to neutral -> exit
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_position = True
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
