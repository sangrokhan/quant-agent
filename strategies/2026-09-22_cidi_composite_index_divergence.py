"""Strategy: Connie Brown's Composite Index Divergence Indicator (CIDI) oversold bounce.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per https://www.quantifiedstrategies.com/composite-index-divergence-indicator/
(Connie Brown, "A New Approach for an Old Problem", MTA Journal 1994), the
Composite Index (CIDI) is a triple-smoothed derivative of the RSI:
    9-period momentum of the 14-period RSI, plus a 3-period SMA of a
    separate 3-period RSI, added together -> an UNBOUNDED oscillator (not
    capped 0-100 like plain RSI). Source's own disclosed backtest rule
    (QQQ, 228 trades, 76% win rate, avg 1%/trade, 17% MDD, 0.03% costs):
        - Long at close when CIDI breaks below 10 (deeply oversold reading
          on this unbounded scale).
        - Exit when today's close ends higher than YESTERDAY's high, or
          after 7 trading days (whichever first).
This is a mean-reversion / oversold-bounce construction, distinct from every
prior RSI-divergence strategy in this repo (which trade divergence swings,
not a single-line absolute-threshold breach) and distinct from all prior
"Composite"/multi-line oscillator constructions (KST, Special K, TDI) since
CIDI's core signal is the raw unbounded RSI-momentum composite value itself,
not a crossover between smoothed lines.

Interface contract for validators (see validation/validators.py) and the
grid tester (see validation/grid_test.py):
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


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _composite_index(
    close: pd.Series,
    rsi_period: int = 14,
    momentum_period: int = 9,
    fast_rsi_period: int = 3,
    fast_sma_period: int = 3,
) -> pd.Series:
    """Connie Brown's Composite Index: unbounded RSI-momentum derivative.

    CI = (RSI(rsi_period) - RSI(rsi_period).shift(momentum_period))
         + SMA(RSI(fast_rsi_period), fast_sma_period)
    """
    rsi_main = _rsi(close, rsi_period)
    rsi_momentum = rsi_main - rsi_main.shift(momentum_period)
    rsi_fast = _rsi(close, fast_rsi_period)
    rsi_fast_sma = rsi_fast.rolling(fast_sma_period).mean()
    return rsi_momentum + rsi_fast_sma


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    momentum_period: int = 9,
    fast_rsi_period: int = 3,
    fast_sma_period: int = 3,
    cidi_entry_threshold: float = 10.0,
    max_hold_days: int = 7,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: CIDI crosses below cidi_entry_threshold (deeply oversold).
    Exit: close > prior day's high, OR max_hold_days elapsed.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    cidi = _composite_index(close, rsi_period, momentum_period, fast_rsi_period, fast_sma_period)
    entry_trigger = cidi < cidi_entry_threshold
    prior_high = high.shift(1)
    exit_trigger = close > prior_high

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    n = len(close)
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
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
