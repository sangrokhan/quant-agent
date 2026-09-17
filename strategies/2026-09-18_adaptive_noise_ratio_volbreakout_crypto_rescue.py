"""Strategy: Adaptive noise-ratio K volatility breakout, RESCUED for crypto
with a leverage-cap position-sizing dial AND a cooldown period to cut
turnover (direct fix for near-miss 2026-09-18-049).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-049 for the
original construction and its rejection):
The original adaptive-K (trailing average noise-ratio) Larry Williams
Volatility Breakout showed a genuinely strong crypto Sharpe (1.26 BTC/1.39
ETH, both above the 1.0 threshold) with excellent parameter stability, but
was rejected on (a) MDD exceeding the 25% cap (27.8% BTC / 34.4% ETH) and
(b) transaction-cost survival failing due to very high turnover (~750-780
trades over the sample from a same-day-exit-every-triggered-day rule). Per
that entry's own notes: "worth a future rescue attempt via either (a) a
leverage cap / vol-target position sizing dial to bring MDD under 25% while
preserving the Sharpe edge ... or (b) widening the exit to a multi-day hold
... to reduce turnover/TC drag." This strategy applies BOTH fixes at once:

1. `leverage_cap` scales every triggered day's exposure down from 1.0 (full
   notional) to a fraction (e.g. 0.6), directly reducing both MDD and daily
   return volatility proportionally.
2. `cooldown_days`: after a triggered trade, suppress new entries for the
   following `cooldown_days` bars even if the breakout condition re-fires.
   This directly cuts `num_trades` (the input to the transaction-cost-drag
   calculation), which was the dominant driver of the TC-survival failure,
   without changing the underlying signal-quality logic.

Signal logic (identical breakout construction to 2026-09-18-049, plus the
two rescue knobs above)
------------------------------------------------------------------
- noise_t = 1 - |close_t-open_t| / (high_t-low_t); K_t = rolling mean of
  noise over `noise_lookback` bars (using data through t-1).
- target_t = open_t + K_t * (high_{t-1} - low_{t-1}).
- Breakout triggers when high_t >= target_t AND (optional) close_{t-1} >
  SMA(trend_window) AND we are not within `cooldown_days` bars of the last
  triggered trade.
- On a triggered day, exposure = leverage_cap for that single day (still a
  same-day round-trip to target_t -> close_t, consistent with the source's
  own "buy today, flat by end of day" rule); 0 otherwise.

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap], though in practice only takes values {0, leverage_cap}
    since this is a same-day-hold breakout, not a persistent position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _noise_ratio(df: pd.DataFrame) -> pd.Series:
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    noise = 1.0 - (df["close"] - df["open"]).abs() / rng
    noise = noise.fillna(1.0).clip(lower=0.0, upper=1.0)
    return noise


def generate_signals(
    price_df: pd.DataFrame,
    noise_lookback: int = 10,
    trend_window: int = 100,
    leverage_cap: float = 0.6,
    cooldown_days: int = 3,
) -> pd.Series:
    """Return an exposure series taking values in {0, leverage_cap}: the
    triggered breakout day's notional exposure, gated by a cooldown period
    since the last triggered trade to cut turnover.
    """
    df = _prep(price_df)
    noise = _noise_ratio(df)
    k = noise.rolling(noise_lookback).mean().shift(1)

    prior_range = (df["high"] - df["low"]).shift(1)
    target = df["open"] + k * prior_range

    raw_breakout = df["high"] >= target

    if trend_window and trend_window > 0:
        sma_trend = df["close"].rolling(trend_window).mean().shift(1)
        trend_ok = df["close"].shift(1) > sma_trend
        raw_breakout = raw_breakout & trend_ok.fillna(False)

    raw_breakout = raw_breakout.fillna(False)

    # Apply cooldown: suppress a trigger if it falls within cooldown_days of
    # the previous accepted trigger.
    triggers = raw_breakout.to_numpy()
    n = len(triggers)
    accepted = np.zeros(n, dtype=bool)
    last_trigger_idx = -10**9
    for i in range(n):
        if triggers[i] and (i - last_trigger_idx) > cooldown_days:
            accepted[i] = True
            last_trigger_idx = i

    exposure = pd.Series(np.where(accepted, leverage_cap, 0.0), index=df.index)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    noise_lookback: int = 10,
    trend_window: int = 100,
    leverage_cap: float = 0.6,
    cooldown_days: int = 3,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    exposure = generate_signals(
        price_df,
        noise_lookback=noise_lookback,
        trend_window=trend_window,
        leverage_cap=leverage_cap,
        cooldown_days=cooldown_days,
    )

    noise = _noise_ratio(df)
    k = noise.rolling(noise_lookback).mean().shift(1)
    prior_range = (df["high"] - df["low"]).shift(1)
    target = df["open"] + k * prior_range

    day_return = (df["close"] / target - 1.0).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    strategy_ret = exposure * day_return
    return strategy_ret
