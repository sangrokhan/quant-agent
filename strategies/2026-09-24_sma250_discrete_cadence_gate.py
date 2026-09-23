"""Strategy: SMA(250) trend-following with a DISCRETE evaluation cadence
(check the regime signal every N trading days and hold, rather than
reacting to every daily close), inspired by an r/LETFs TQQQ+SMA250
backtest thread.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per a recent r/LETFs thread "TQQQ + SMA 250 Backtest: Analysis and Request
for Community Feedback" (read via Google AI-overview summary + SERP
snippets this iteration -- web_search DDGS backend used successfully for
the RSI(2)/Connors search earlier this iteration but this specific Reddit
query needed browser_exec Google fallback), the thread's disclosed
methodology: hold the leveraged ETF while the underlying index closes
above its 250-day SMA (risk-on), flat/cash when below (risk-off) -- BUT
crucially, the signal is only RE-EVALUATED every 10 trading days
(~semi-monthly), not on every daily close. The thread's own stated
rationale is that checking every 10 days ("whipsaw reduction") stops daily
market noise from triggering costly transitions, at the cost of some lag
risk on fast V-shaped reversals.

This repo has 500+ prior entries using SMA(200)/SMA(250) trend gates with
DAILY re-evaluation (continuous signal), but this discrete-cadence
construction -- deliberately widening the decision interval to trade off
whipsaw reduction against reaction lag -- has not been tested as its own
mechanism. Adapted here to this repo's non-leveraged QQQ/SPY/BTC/ETH
universe (no leveraged-ETF loader exists in data/loaders.py) as a direct
long/cash trend-following signal rather than a leverage-tier rotation, to
isolate whether the DISCRETE CADENCE itself (vs continuous daily
re-evaluation of the identical SMA gate) changes the risk-adjusted return
profile.

Signal logic
------------
- Every eval_interval trading days, re-evaluate: is close > SMA(sma_window)?
  If yes, target position = 1 (long); if no, target position = 0 (flat).
- Between evaluation days, HOLD the last-set target position regardless of
  what price does intra-cadence (this is the entire point of the test --
  no daily reactivity).
- No separate exit rule beyond the next scheduled evaluation.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position).
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
    sma_window: int = 250,
    eval_interval: int = 10,
) -> pd.Series:
    """Return a 0/1 long/flat position series, re-evaluated every eval_interval bars."""
    df = _prep(price_df)
    close = df["close"]
    sma = close.rolling(sma_window).mean()
    raw_signal = (close > sma).fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    current = 0
    for i in range(len(df)):
        if i % eval_interval == 0:
            current = int(bool(raw_signal.iloc[i]))
        position.iloc[i] = current
    return position


def generate_returns(
    price_df: pd.DataFrame,
    sma_window: int = 250,
    eval_interval: int = 10,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(price_df, sma_window=sma_window, eval_interval=eval_interval)
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
