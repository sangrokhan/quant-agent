"""Strategy: RSI(14) 45/75 asymmetric-threshold swing mean reversion
("RSI 14 Debunked -- Do This Instead" own disclosed best-optimized rule).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-083):
Per QuantifiedStrategies.com's "RSI 14 Debunked" article
(https://www.quantifiedstrategies.com/rsi-14-debunked/, visited this
iteration), the source ran an Amibroker optimization sweep of buy
thresholds {45,40,35,30,25} x sell thresholds {55,60,65,70,75} on the
STANDARD 14-day RSI (S&P 500, 1993-present) and disclosed the single
best-performing combo by CAGR: buy (go long) when the 14-day RSI drops
below 45, sell (exit to flat) when the 14-day RSI rises above 75. The
source's own finding is a NEGATIVE result -- this best-of-25-combos
config still UNDERPERFORMS buy-and-hold on raw CAGR (8.51% vs 10.1%) with
an IDENTICAL max drawdown (55%) to buy-and-hold, i.e. no risk-adjusted
benefit despite being the single best combination in their own sweep.

This is a genuinely distinct RSI construction from every prior RSI
strategy in this repo: it uses the STANDARD 14-day RSI (not RSI(2) or a
composite/adaptive variant), a WIDE ASYMMETRIC threshold band (45/75, not
a symmetric oversold/overbought pair like 30/70), and NO trend filter
(unlike 2026-09-03-005's RSI2+SMA200 trend gate) -- isolating whether the
source's own claimed "best" config, taken completely at face value and
implemented independently on this repo's own data/vectorbt pipeline,
actually clears this repo's own Sharpe/MDD/TC-survival bar (a genuinely
open question since the source's own writeup only reports CAGR and
max-drawdown, not Sharpe or transaction-cost-adjusted returns).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
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
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    buy_threshold: float = 45.0,
    sell_threshold: float = 75.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series: enter long on the close
    where RSI(rsi_window) drops below buy_threshold (if not already
    long), exit to flat on the close where RSI rises above sell_threshold.
    Once in a position, stay long until the sell condition triggers
    (source's own rule has no separate stop/time-exit)."""
    df = _prep(price_df)
    close = df["close"]
    rsi = _rsi(close, rsi_window)

    buy_signal = rsi < buy_threshold
    sell_signal = rsi > sell_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(sell_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(buy_signal.iloc[i]):
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
    strategy_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strategy_ret
