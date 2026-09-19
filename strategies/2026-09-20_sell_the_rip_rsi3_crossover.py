"""Strategy: Sell-the-Rip -- 3-day RSI oversold-entry / overbought-exit crossover on SPY.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-058):
Per quantifiedstrategies.com's "Sell the Rip Trading Strategy: Trading
Rules, Setup, Risk, And Backtest"
(https://www.quantifiedstrategies.com/sell-the-rip-strategy/, visited this
iteration via browser_exec fallback -- web_search DDGS backend hit
repeated TLS/connection-reset errors on every query attempted), the
article discloses a concrete baseline rule in its free body text: "When
the 3-day RSI is below 30, we go long at the close. When the 3-day RSI
crosses above 70, we sell the rip at the close." (backtested on SPY since
1993: 391 trades, avg gain 0.61%/trade, win rate 75%, profit factor 1.6,
MDD -39%). The source itself judges this baseline "far from tradable"
due to drawdown size, and reports (without disclosing the exact improved
rule, which is paywalled) that a different, more aggressive exit
materially improves the equity curve and cuts MDD to -24%.

This repo tests the source's own disclosed BASELINE rule exactly as
stated: long when RSI(3) < entry_threshold (30), exit ("sell the rip")
when RSI(3) crosses above exit_threshold (70), both at the close, plus a
max_hold_days safety backstop.

Distinct from this repo's already-accepted 2026-09-18-095 (3-day RSI
oversold bounce, SPY accepted): that strategy used entry_threshold=20 and
a signal-based exit ("close crosses above yesterday's high"), NOT an
RSI-recrossing-70 exit. This entry tests the source's different,
narrower entry/exit pair (30/70 pure RSI-crossover-based exit, no price
levels involved) as a genuinely distinct construction, explicitly
expecting to reproduce/confirm the source's own "far from tradable"
finding (large MDD) under this repo's validator suite, per
RESEARCH_LOOP.md's requirement to test hypotheses actually read this run
rather than skip them because a prior related idea worked.

Source: https://www.quantifiedstrategies.com/sell-the-rip-strategy/ (the
improved/paywalled exit rule referenced in the article is NOT implemented
here -- only the fully disclosed baseline rule).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: 1 long/0 flat)
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


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 3,
    entry_threshold: float = 30.0,
    exit_threshold: float = 70.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_period)
    entry = rsi < entry_threshold
    # "crosses above" exit_threshold: today's RSI >= threshold and
    # yesterday's RSI was below it.
    exit_cross = (rsi >= exit_threshold) & (rsi.shift(1) < exit_threshold)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or held >= max_hold_days:
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
