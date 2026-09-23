"""Strategy: Dual-SMA trend + RSI oversold-turn-up entry, fixed holding-period exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per Sofien Kaabar, CFA, "I Backtested a Powerful Strategy on Bitcoin - The
Results" (https://abouttrading.substack.com/p/i-backtested-a-powerful-strategy,
read via browser_exec this iteration -- web_search DDGS backend returned
generic listicle results for several other queries this run before this one
succeeded). Source's disclosed "Bull-only" rule, tuned on daily BTC-USD:

  "A bullish trade is generated whenever the current short-term SMA is
  above the current long-term SMA and the previous RSI is below the
  oversold level and below the current RSI."

Source's own disclosed bull-only parameters: short_len=200, long_len=300,
rsi_ov=60, rsi_us=35, holding_period=20 (bars). The distinctive, genuinely
novel-in-this-repo construction here is the FIXED holding-period-only exit
(liquidate exactly N bars after entry, no trend-flip exit, no RSI-exit, no
stop-loss) combined with unusually LONG SMA lookbacks (200/300, well beyond
the more common 20/50/50-200 pairs already tested repeatedly in this repo)
and an RSI TURNING-UP-FROM-BELOW-OVERSOLD condition (not a static
threshold-touch) as the trigger, layered on top of (not instead of) the
SMA trend filter.

This differs from this repo's many other SMA+RSI combination entries
(dual-oversold gates, RSI(2) mean-reversion variants, RSI dynamic-zone
recross, etc.) specifically in: (a) both SMA windows are far longer
(200/300 vs the usual <=50-200 pair), (b) exit is PURELY time-based
(holding_period bars), not tied to any indicator crossing back, and (c) the
RSI condition requires the PREVIOUS bar's RSI below the oversold level AND
the CURRENT bar's RSI above the previous bar's RSI (a turn, not a level).

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
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


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    short_len: int = 200,
    long_len: int = 300,
    rsi_period: int = 14,
    rsi_us: float = 35.0,
    holding_period: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: SMA(short_len) > SMA(long_len) AND previous-bar RSI < rsi_us AND
    current-bar RSI > previous-bar RSI (turning up from oversold, in an
    established uptrend). Exit: exactly `holding_period` bars after entry
    (fixed time-stop, no other exit condition) -- if a new entry signal
    fires while already in a position, it's ignored (no re-entry/pyramiding
    until the current holding period completes).
    """
    df = _prep(price_df)
    close = df["close"]

    sma_short = close.rolling(short_len).mean()
    sma_long = close.rolling(long_len).mean()
    trend_ok = sma_short > sma_long

    rsi = _rsi(close, rsi_period)
    rsi_prev = rsi.shift(1)
    entry_signal = trend_ok.fillna(False) & (rsi_prev < rsi_us) & (rsi > rsi_prev)
    entry_signal = entry_signal.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= holding_period:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    short_len: int = 200,
    long_len: int = 300,
    rsi_period: int = 14,
    rsi_us: float = 35.0,
    holding_period: int = 20,
) -> pd.Series:
    """Daily strategy returns: position(t-1) * price_return(t) (no lookahead)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        short_len=short_len,
        long_len=long_len,
        rsi_period=rsi_period,
        rsi_us=rsi_us,
        holding_period=holding_period,
    )
    price_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(float) * price_returns
    return strat_returns
