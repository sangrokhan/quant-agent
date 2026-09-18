"""Strategy: Plain RSI(14) mean-reversion, standalone (no trend filter),
long-only -- the exact CoinQuant "library baseline" rule.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-010):
Per CoinQuant's "ADA RSI Strategy Backtest: Does Cardano's Volatility Make
RSI Signals More Effective?"
(https://www.coinquant.ai/blog/ada-rsi-strategy-backtest-does-cardano-s-volatility-make-rsi-signals-more-effective,
found via browser_exec Google fallback after web_search DDGS backend
returned unusable results this iteration): CoinQuant's published "library
baseline" RSI mean-reversion rule (long only, one position at a time,
100% equity per entry) is:
    Entry: RSI(14) (Wilder-smoothed) crosses below 30
    Exit:  RSI(14) crosses back above 50
No trend filter, no volume confirmation, no divergence detection -- a
genuinely standalone RSI(14) oversold-bounce rule. CoinQuant's own
published backtest (Aug 2021-Aug 2026, BTC/USDT spot, Binance, daily bars)
reports +55.69% total return, 13 trades, 61.5% win rate, Sharpe 0.48,
Sortino 0.77, MDD 23.19%, profit factor 3.04. This repo tests the
identical rule (unmodified) on this repo's own data source/date range to
see if it independently replicates.

This is distinct from every prior RSI(14)-family entry in this repo's
knowledge base: 2026-09-03-019 requires DIVERGENCE (price/RSI diverging
at swing lows), 2026-09-05-083 requires VOLUME confirmation,
2026-09-11-083 uses ASYMMETRIC 45/75 thresholds (not the standard 30/50),
2026-09-09-074 uses a DUAL-RSI (14+21) agreement construction. None of
those prior entries tested the plain, single-condition, standard-threshold
(30 entry / 50 exit) RSI(14) crossover with no other filter -- exactly the
rule CoinQuant published and directly attributes Bitcoin's positive
five-year track record to.

Interface contract for validators (see validation/validators.py) and
grid_test.py: both generate_signals and generate_returns accept all
tunable parameters as keyword arguments.
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
    """Wilder's RSI (standard exponential smoothing, alpha=1/window)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    rsi_entry: float = 30.0,
    rsi_exit: float = 50.0,
) -> pd.Series:
    """Long-only {0,1} position series, no trend filter."""
    df = _prep(price_df)
    close = df["close"]
    rsi = _rsi(close, rsi_window)

    below_entry = rsi < rsi_entry
    above_exit = rsi > rsi_exit
    # Crossing detection: entry when RSI crosses below the entry threshold
    # (was >= entry yesterday, is < entry today); exit when RSI crosses
    # above the exit threshold.
    entry_trigger = (below_entry & ~below_entry.shift(1).fillna(False)).fillna(False)
    exit_trigger = (above_exit & ~above_exit.shift(1).fillna(False)).fillna(False)

    in_position = False
    pos_vals = [0] * len(close)
    entry_vals = entry_trigger.values
    exit_vals = exit_trigger.values
    for i in range(len(pos_vals)):
        if in_position:
            if exit_vals[i]:
                in_position = False
                pos_vals[i] = 0
            else:
                pos_vals[i] = 1
        else:
            if entry_vals[i]:
                in_position = True
                pos_vals[i] = 1
            else:
                pos_vals[i] = 0
    position = pd.Series(pos_vals, index=close.index, dtype=int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
