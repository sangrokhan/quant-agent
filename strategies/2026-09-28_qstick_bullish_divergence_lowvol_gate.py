"""Strategy: Qstick (Chande) bullish price/indicator divergence,
LOW-VOL REGIME GATED (follow-up rescue for near-miss 2026-09-09-088).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-28-043):
The original Qstick bullish-divergence strategy (2026-09-09-088,
strategies/2026-09-09_qstick_bullish_divergence.py) was rejected on a
full-sample basis (QQQ Sharpe -0.249, SPY Sharpe 0.112) but its own grid
test's own notes explicitly flagged: "edge concentrated almost entirely in
low-vol regimes... by_vol_regime low 14/72, mid 4/72, high 2/72... Best
regime-sliced cell (SPY, low-vol): Sharpe 2.07... Worth revisiting:
explicitly gate this signal to trade only in the low-vol tercile (like
2026-09-03_bb_meanrev_qqq_volregime.py) in a future iteration." No later
iteration in this repo picked up that flagged near-miss until now.

This iteration adds an explicit realized-volatility regime AND-gate (20d
realized vol <= vol_regime_ratio x its own trailing 252d median, identical
construction to strategies/2026-09-03_bb_meanrev_qqq_volregime.py) on top
of the existing Qstick bullish-divergence + zero-cross entry, plus a
risk-off exit if the regime flips to high-vol mid-trade -- exactly the fix
the prior iteration's own notes recommended.

Signal logic (daily bars, causal/no look-ahead):
1. Low-vol regime filter: 20-day realized vol (annualized std of daily log
   returns) <= vol_regime_ratio (default 1.0) x its own trailing 252-day
   median.
2. Qstick = SMA(qstick_window) of (close - open).
3. Bullish divergence: price makes a new `swing_lookback`-bar low (close
   <= rolling min close) while Qstick is ABOVE its own value at the prior
   new-low bar within that window (Qstick "higher low" vs price "lower
   low").
4. Entry (long): divergence condition flagged recently (within the
   lookback window) AND Qstick crosses back above zero (confirmation
   trigger, same as the original strategy) AND the low-vol regime filter
   holds.
5. Exit: Qstick crosses back below zero, OR the volatility regime flips
   to high-vol (risk-off exit), OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and
validation/grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _qstick(df: pd.DataFrame, qstick_window: int) -> pd.Series:
    body = df["close"] - df["open"]
    return body.rolling(qstick_window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    qstick_window: int = 14,
    swing_lookback: int = 15,
    max_hold_days: int = 15,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    qstick = _qstick(df, qstick_window)

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = realized_vol <= (vol_median_1y * vol_regime_ratio)

    rolling_min_close = close.rolling(swing_lookback).min()
    is_price_low = close <= rolling_min_close

    prior_low_qstick = qstick.rolling(swing_lookback).apply(
        lambda window: window.iloc[0] if len(window) else float("nan"), raw=False
    )

    bullish_divergence = is_price_low & (qstick > prior_low_qstick)
    divergence_recent = bullish_divergence.fillna(False).rolling(swing_lookback, min_periods=1).max().astype(bool)

    qstick_cross_up = (qstick > 0) & (qstick.shift(1) <= 0)
    qstick_cross_down = (qstick < 0) & (qstick.shift(1) >= 0)

    entry = divergence_recent & qstick_cross_up.fillna(False) & low_vol_regime.fillna(False)
    exit_regime_flip = ~low_vol_regime.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    n = len(close)
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if (
                bool(qstick_cross_down.iloc[i])
                or bool(exit_regime_flip.iloc[i])
                or held >= max_hold_days
            ):
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
