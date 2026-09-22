"""Strategy: SPY RSI(3) pullback entry, prior-day-high rebound exit,
200-day trend filter (QuantifiedStrategies "AI Found a Profitable SPY
Strategy" thought experiment).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per QuantifiedStrategies.com's X/Twitter thread "AI Found a Profitable SPY
Strategy in 30 Seconds. Then We Tried to Break It."
(https://x.com/QuantifiedStrat/article/2101677169235652639, read via
browser_exec this iteration -- web_extract cannot render X.com articles),
a deliberately simple long-only pullback strategy: enter when SPY closes
above its own 200-day SMA (long-term uptrend intact) AND RSI(3) closes
below 20 (short-term oversold pullback within that uptrend); buy at the
next session's open. Exit at the next session's open after SPY's close
first exceeds the PREVIOUS day's high (a rebound-confirmation exit, not a
fixed RSI-level or moving-average-recross exit). No stop-loss, no profit
target, one position at a time.

The source's own robustness claims (full 1993-2026 SPY backtest: 253
trades, 75.9% win rate, profit factor 2.60, -11.7% closed-trade max
drawdown; survived RSI length 2-5 / threshold 10-30 sweeps, MA length
150-250 sweeps, 6 alternate exits, 20bps cost drag, and 4 market eras) are
exactly what this iteration's grid-test + validator suite independently
re-checks rather than trusts at face value.

This is distinct from this repo's existing RSI mean-reversion entries:
- 2026-09-03-005 (RSI(2)/SMA(5)-recovery exit)
- 2026-09-10 RSI(4)/RSI(55)-level exit (see strategies/2026-09-10_rsi4_200sma_55exit.py)
Both use fixed RSI-level or MA-recross exits; this strategy's exit
("close breaks above the PRIOR day's high") is a distinct price-action
rebound-confirmation rule not previously tested in this repo (0 matches
for "prior.day.*high.*exit"/"rebound exit" in strategies_index.jsonl).

Signal logic
------------
- Trend filter: close > SMA(trend_window) (default 200).
- Entry (long): close > SMA(trend_window) AND RSI(rsi_window) < entry_threshold
  (RSI(3) < 20 by default). Enter at NEXT bar's open (approximated here by
  shifting the position series by one extra bar relative to signal date,
  consistent with generate_returns' existing next-bar-return convention).
- Exit: close > close.shift(1) rolling max of the PRIOR bar's high (i.e.
  today's close exceeds yesterday's high) -> exit at next bar's open. Also
  bounded by a max_hold_days time-stop backstop (source discloses no
  stop-loss/profit-target, but an unbounded hold is unsafe for the grid
  framework, so we add a generous time-stop as backstop only).
- Flat otherwise. Long-only, one position at a time (no pyramiding).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.fillna(50.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    rsi_window: int = 3,
    entry_threshold: float = 20.0,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    sma = close.rolling(trend_window).mean()
    rsi = _rsi(close, rsi_window)

    uptrend = close > sma
    oversold = rsi < entry_threshold
    entry = (uptrend & oversold).fillna(False)

    prior_high = high.shift(1)
    exit_signal = (close > prior_high).fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(df)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift by 1: yesterday's signal determines today's return exposure,
    # approximating the source's "enter/exit at next session's open".
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
