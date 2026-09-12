"""Strategy: Bollinger Band Lower-Touch Mean Reversion on SOL/USDT (and
XRP/USDT), targeting a documented recent (Nov 2025-May 2026) chop/downtrend
regime where mean-reversion reportedly outperformed trend-following.

Source: CoinQuant.ai "We Tested 5 Strategies on Solana: Which One
Backtested Best?" (https://www.coinquant.ai/blog/we-tested-5-strategies-
on-solana-which-one-backtested-best, read via browser_exec this iteration
-- web_search DDGS backend TLS-erroring on every query attempted). Source's
own head-to-head 6-month backtest (Nov 2025-May 2026, SOL/USDT 4h) found
Bollinger Bands(20,2) lower-touch mean reversion was the ONLY profitable
approach of 5 tested (+10.4% vs buy-and-hold -27.9%; Sharpe 0.65, 71.4% win
rate, 21 trades), while every SMA/MACD trend-following variant lost money
during the same window.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's
id): this repo's existing accepted Bollinger Band mean-reversion strategy
(2026-09-03_bb_meanrev_qqq_volregime.py, id 2026-09-03-001) has never been
tested on SOL/USDT or any altcoin beyond BTC/ETH (confirmed via
2026-09-13-027's grid, which showed BTC/ETH/XRP RSI mean reversion failing
decisively over the FULL multi-year sample -- a different indicator family
and a much longer window than this source's narrow 6-month test). This
iteration re-tests the SAME Bollinger-lower-touch mean-reversion mechanism
already proven on equities, but on SOL/USDT and XRP/USDT specifically,
over this repo's full available crypto history (not just the source's
narrow 6-month window) to see if it holds up out of the source's own
cherry-picked regime.

Signal logic
------------
- Daily-resampled close (crypto loader default is hourly).
- bb_window/bb_std: standard Bollinger Band construction (source's own
  20-period/2-std default).
- Entry (long): close crosses below the lower Bollinger Band.
- Exit: close crosses back above the middle Bollinger Band (basis SMA),
  or a max_hold_days time-stop (source's own test had no explicit
  time-stop; added here per this repo's standard practice to avoid
  indefinite holds).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
"""

from __future__ import annotations

import pandas as pd


def _prep_daily(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    daily = df["close"].resample("1D").last().dropna()
    return pd.DataFrame({"close": daily})


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series (daily bars)."""
    df = _prep_daily(price_df)
    close = df["close"]

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    lower_band = sma - bb_std * std

    entry_cond = (close < lower_band).fillna(False)
    exit_cond = (close > sma).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cond.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_cond.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs), daily bars."""
    df = _prep_daily(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
