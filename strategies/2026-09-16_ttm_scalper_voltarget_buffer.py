"""Strategy: John Carter TTM Scalper reversal-confirmation base signal +
inverse-volatility position sizing overlay with no-trade rebalance buffer,
for the SPY double near-miss rescue.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Direct fix for prior id 2026-09-16-135 (TTM Scalper reversal-confirmation:
QQQ accepted, SPY double near-miss Sharpe 0.866<1.0 AND MDD 0.261>0.25
simultaneously, crypto decisively rejected 0/36 grid cells -- crypto is a
signal-quality failure, not attempted here). Adds this repo's already-
validated inverse-volatility position-sizing overlay with a no-trade
rebalance buffer (construction unchanged from 2026-09-07-026) on top of
the unchanged TTM Scalper base signal, for SPY only (QQQ already accepted
without an overlay; crypto's decisive signal-quality failure isn't fixable
by a sizing overlay alone). No new external research this sub-iteration --
TTM Scalper source unchanged from 2026-09-16-135
(https://www.tradingview.com/script/CddpDBGA-TTM-scalper-indicator-Strategy/).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, vol_cap]).
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


def _ttm_scalper_base_signal(close: pd.Series) -> pd.Series:
    c = close.to_numpy()
    n = len(c)

    trigger_sell = np.zeros(n, dtype=bool)
    trigger_buy = np.zeros(n, dtype=bool)
    for i in range(3, n):
        up_move = c[i - 1] < c[i]
        down_move = c[i - 1] > c[i]
        confirm_sell = (c[i - 2] < c[i - 1]) or (c[i - 3] < c[i - 1])
        confirm_buy = (c[i - 2] > c[i - 1]) or (c[i - 3] > c[i - 1])
        trigger_sell[i] = up_move and confirm_sell
        trigger_buy[i] = down_move and confirm_buy

    buy_sell_switch = np.zeros(n, dtype=bool)
    pos = np.zeros(n)
    for i in range(1, n):
        prev_switch = buy_sell_switch[i - 1]
        if trigger_sell[i]:
            buy_sell_switch[i] = True
        elif trigger_buy[i]:
            buy_sell_switch[i] = False
        else:
            buy_sell_switch[i] = prev_switch

        if trigger_sell[i] and not prev_switch:
            pos[i] = -1.0
        elif trigger_buy[i] and prev_switch:
            pos[i] = 1.0
        else:
            pos[i] = pos[i - 1]

    return pd.Series((pos == 1.0).astype(float), index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    vol_window: int = 20,
    target_vol: float = 0.15,
    vol_cap: float = 1.0,
    rebalance_buffer: float = 0.10,
) -> pd.Series:
    """Continuous {0..vol_cap} position-size series: TTM Scalper base
    signal scaled by inverse-volatility targeting, with a no-trade
    rebalance buffer to cut turnover.
    """
    df = _prep(price_df)
    close = df["close"]

    base_signal = _ttm_scalper_base_signal(close)

    log_ret = np.log(close / close.shift(1))
    realized_vol = log_ret.rolling(vol_window).std() * np.sqrt(252.0)
    raw_scale = (target_vol / realized_vol).clip(upper=vol_cap)
    raw_scale = raw_scale.fillna(0.0)
    desired_size = (base_signal * raw_scale).clip(lower=0.0, upper=vol_cap)

    held = np.zeros(len(desired_size))
    desired = desired_size.to_numpy()
    current = 0.0
    for i in range(len(desired)):
        if abs(desired[i] - current) > rebalance_buffer:
            current = desired[i]
        held[i] = current
    return pd.Series(held, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    vol_window: int = 20,
    target_vol: float = 0.15,
    vol_cap: float = 1.0,
    rebalance_buffer: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day held size * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    held = generate_signals(
        price_df,
        vol_window=vol_window,
        target_vol=target_vol,
        vol_cap=vol_cap,
        rebalance_buffer=rebalance_buffer,
    )
    daily_ret = close.pct_change().fillna(0.0)
    return held.shift(1).fillna(0.0) * daily_ret
