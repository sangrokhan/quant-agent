"""Strategy: SMA(20) 2%-breakout entry, RSI(14) cross-up-through-30 exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-XXX):
Per a Medium/Kryptera article ("Why This Strategy Beat Buy-and-Hold and
Still Drew Down 85%", https://medium.com/@Kryptera/why-this-strategy-beat-
buy-and-hold-and-still-drew-down-85-89d2c717eccf, read via browser_exec
this iteration -- web_search DDGS/Yahoo backend TLS-errored on every query
attempted), a deliberately minimal 2-rule system: ENTRY when close closes
more than a threshold pct (default 2%) above its own 20-day SMA (a
momentum-breakout confirmation, not a simple crossover -- price must be
CLEARLY above the average, not just marginally), EXIT when the 14-period
RSI crosses back UP through 30 from below (i.e. exits when RSI recovers out
of oversold territory -- since entry only fires on strength, an oversold
RSI reading after entry signals the trade has already drawn down
meaningfully and this exit crystallizes that reversal rather than waiting
for a fresh downtrend confirmation). The source's own headline explicitly
warns this system still drew down 85% on its RCL test case despite beating
buy-and-hold on raw walk-forward Sharpe -- this repo tests the rule
directly on QQQ/SPY/BTC/ETH rather than trusting the source's single-stock
claim, per RESEARCH_LOOP.md's grounding requirement.

Distinct from prior repo entries: no other strategy in this KB combines an
UNCONDITIONAL SMA-breakout-by-a-fixed-percentage entry with an RSI-recovery
(crossing UP through an oversold threshold, not down through an overbought
one) as the SOLE exit trigger -- most repo RSI exits either fade at
overbought or use RSI crossing DOWN through a threshold as a bearish signal.

Signal logic
------------
- Entry (long): close > SMA(sma_window) * (1 + breakout_pct).
- Exit: RSI(rsi_window) crosses from <= rsi_exit_threshold on the prior bar
  to > rsi_exit_threshold on the current bar (i.e. RSI recovering UP
  through the oversold line), OR a max_hold_days time-stop as a safety
  backstop the source's own minimal 2-rule system lacks.

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
    sma_window: int = 20,
    breakout_pct: float = 0.02,
    rsi_window: int = 14,
    rsi_exit_threshold: float = 30.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(sma_window).mean()
    entry = close > sma * (1 + breakout_pct)

    rsi = _rsi(close, rsi_window)
    rsi_prev = rsi.shift(1)
    exit_rsi_cross_up = (rsi_prev <= rsi_exit_threshold) & (rsi > rsi_exit_threshold)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_rsi_cross_up.iloc[i]) or held >= max_hold_days:
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
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
