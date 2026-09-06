"""Strategy: SMA200 trend-following base signal + inverse-volatility position
sizing overlay WITH a no-trade rebalance buffer band.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-026):
Source: https://blave.org/agent/en/learn/vol_targeting (accessed 2026-09-07).
The page describes continuous inverse-volatility position sizing:
    scale = clip(target_vol / realized_vol, upper=vol_cap)
    scaled_signal = base_signal * scale
applied on top of a binary base signal, to keep dollar risk roughly constant
across volatility regimes instead of taking the same full-size bet whether
the market is calm or chaotic.

This is a direct, targeted follow-up to the previously-REJECTED
2026-09-03-003 (BTC absolute-momentum + vol-target overlay, crypto-only):
that attempt improved Sharpe (1.24, passed) and materially cut MDD (66%->
47.6%) versus its un-scaled predecessor, but still failed the MDD budget
(35%) AND failed transaction-cost survival because the validator counted
every daily vol-driven position-size wiggle as a discrete trade (~1231
trades / 2801 days). That entry's own notes proposed exactly the fix
implemented here: "add a min_rebalance_threshold ... so continuous-sizing
strategies aren't penalized for daily vol noise" -- i.e. the "No-Trade
Region (Buffer)" the source page itself recommends (10-15% band: only
rebalance when the newly-computed target size differs from the currently
held size by more than `rebalance_buffer`).

This iteration also broadens scope: instead of crypto-only momentum, the
base signal here is a simple, well-understood SMA(trend_window) trend
filter (long when close > SMA), tested on BOTH equity and crypto, so we can
see whether the buffered vol-targeting overlay is a generically useful
risk-management wrapper (as the source claims) or something crypto/BTC
tail-risk specific.

Signal logic
------------
- Base binary signal: 1 if close > SMA(trend_window), else 0 (long-only
  trend-following, no shorts).
- Realized vol: rolling std of daily log returns over `vol_window`,
  annualized (* sqrt(252)).
- Raw scale = target_vol / realized_vol, capped at `vol_cap` (and floored
  at 0 when realized_vol is NaN/zero, e.g. warm-up period -> flat).
- Desired continuous position = base_signal * raw_scale (0 when base
  signal is 0, i.e. we never short even if vol is very low).
- No-trade buffer: the ACTUALLY HELD position only updates to the newly
  desired size when it differs from the previous day's held size by more
  than `rebalance_buffer` (e.g. 0.10 = 10%); otherwise carry forward
  yesterday's held size unchanged. This is what should cut the trade count
  that sank 2026-09-03-003's transaction-cost survival.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
        Continuous {0..vol_cap} position-size series (NOT strictly {0,1}
        since this is a sized/leveraged overlay) aligned to price_df.index.
    generate_returns(price_df, **params) -> pd.Series
        Daily strategy returns using the held (buffered) position size,
        no transaction costs applied here (handled by
        check_transaction_cost_survival separately).
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


def _compute_desired_size(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    vol_window: int = 20,
    target_vol: float = 0.30,
    vol_cap: float = 2.0,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window, min_periods=trend_window).mean()
    base_signal = (close > sma).astype(float)
    base_signal = base_signal.where(sma.notna(), 0.0)

    log_ret = np.log(close / close.shift(1))
    realized_vol = log_ret.rolling(vol_window, min_periods=vol_window).std() * (252 ** 0.5)

    raw_scale = target_vol / realized_vol
    raw_scale = raw_scale.replace([np.inf, -np.inf], np.nan).clip(upper=vol_cap)
    raw_scale = raw_scale.fillna(0.0)

    desired = base_signal * raw_scale
    return desired.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    vol_window: int = 20,
    target_vol: float = 0.30,
    vol_cap: float = 2.0,
    rebalance_buffer: float = 0.10,
) -> pd.Series:
    """Return the continuous (buffered) held position-size series."""
    desired = _compute_desired_size(
        price_df,
        trend_window=trend_window,
        vol_window=vol_window,
        target_vol=target_vol,
        vol_cap=vol_cap,
    )

    held = pd.Series(index=desired.index, dtype=float)
    prev_held = 0.0
    desired_vals = desired.to_numpy()
    held_vals = np.empty(len(desired_vals), dtype=float)
    for i in range(len(desired_vals)):
        d = desired_vals[i]
        if abs(d - prev_held) > rebalance_buffer:
            prev_held = d
        held_vals[i] = prev_held
    held[:] = held_vals
    return held


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    vol_window: int = 20,
    target_vol: float = 0.30,
    vol_cap: float = 2.0,
    rebalance_buffer: float = 0.10,
) -> pd.Series:
    """Return daily strategy returns (no transaction costs applied)."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change()

    position = generate_signals(
        price_df,
        trend_window=trend_window,
        vol_window=vol_window,
        target_vol=target_vol,
        vol_cap=vol_cap,
        rebalance_buffer=rebalance_buffer,
    )
    # Position at t is decided using info through t (SMA/vol computed on
    # close up to t); apply to next day's return to avoid lookahead.
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret.fillna(0.0)
