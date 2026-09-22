"""Strategy: Percentile Channel hysteresis + daily formation-price stop-loss.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-043):
Direct rescue attempt for this cron trigger's own prior near-miss rejection
(2026-09-22-042, percentile-channel-with-hysteresis QQQ trend/cash switch,
Sharpe 1.019 pass but decisive MDD 0.2856 fail from a monthly-rebalanced
signal reacting too slowly to the COVID crash -- identical MDD value also
seen in the same-cron-trigger 2026-09-22-040 composite-momentum entry,
confirming a monthly-cadence circuit-breaker cannot control this
particular drawdown event). This sub-iteration reuses the repo's
already-accepted daily-reacting formation-price stop-loss overlay
mechanism (strategies/2026-09-08_formation_price_stoploss_trend.py, per
Han/Zhou/Zhu "Taming Momentum Crashes: A Simple Stop-Loss Strategy",
https://www.cxoadvisory.com/technical-trading/stop-losses-to-avoid-stock-momentum-crashes/,
successfully applied to rescue the TSMOM boundary-gate entry in
2026-09-22-038) on top of the IDENTICAL, otherwise-unmodified percentile
channel entry/exit logic from 2026-09-22-042: exit immediately (go flat,
checked every trading day, not just at the monthly rebalance) if close
falls below the position's own entry price by more than `stop_loss_pct`;
re-entry only waits for the next monthly rebalance's fresh percentile-rank
entry trigger.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  (0/1 position series)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _pct_rank(close: pd.Series, window: int) -> pd.Series:
    def rank_last(x):
        return (x <= x[-1]).sum() / len(x)

    return close.rolling(window).apply(rank_last, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 252,
    entry_threshold: float = 0.7,
    exit_threshold: float = 0.25,
    rebalance_days: int = 21,
    stop_loss_pct: float = 0.15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    pct_rank = _pct_rank(close, window)
    n = len(df)

    # Monthly-rebalanced "desired" state from the base percentile-channel
    # hysteresis logic (identical to 2026-09-22-042).
    desired = pd.Series(0, index=df.index, dtype=int)
    held_desired = 0
    for i in range(n):
        if i % rebalance_days == 0:
            r = pct_rank.iloc[i]
            if pd.notna(r):
                if held_desired == 0 and r > entry_threshold:
                    held_desired = 1
                elif held_desired == 1 and r < exit_threshold:
                    held_desired = 0
        desired.iloc[i] = held_desired
    desired.iloc[:window] = 0

    # Daily-checked stop-loss overlay: within a desired-long span, exit
    # early (go flat) if the close drops below the entry price by more
    # than stop_loss_pct; only re-enter once desired flips back to 1 on a
    # later bar (natural since desired only updates monthly, so a stop-out
    # effectively skips the rest of that same span; re-entry happens at
    # the following rebalance if percentile rank is still favorable, since
    # `desired` doesn't reset itself -- so we explicitly track a
    # stopped_out flag until desired transitions 0->1 again).
    positions = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_price = None
    stopped_out_pending = False
    prev_desired = 0
    close_vals = close.values
    desired_vals = desired.values

    for i in range(n):
        d = desired_vals[i]
        if d == 1 and prev_desired == 0:
            stopped_out_pending = False  # fresh signal transition resets stop memory

        if d == 0:
            in_position = False
            entry_price = None
            positions.iloc[i] = 0
        else:
            if stopped_out_pending:
                positions.iloc[i] = 0
            else:
                if not in_position:
                    in_position = True
                    entry_price = close_vals[i]
                px = close_vals[i]
                stop_price = entry_price * (1.0 - stop_loss_pct)
                if px < stop_price:
                    in_position = False
                    stopped_out_pending = True
                    positions.iloc[i] = 0
                else:
                    positions.iloc[i] = 1
        prev_desired = d

    return positions.fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    window: int = 252,
    entry_threshold: float = 0.7,
    exit_threshold: float = 0.25,
    rebalance_days: int = 21,
    stop_loss_pct: float = 0.15,
) -> pd.Series:
    df = _prep(price_df)
    positions = generate_signals(
        df,
        window=window,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        rebalance_days=rebalance_days,
        stop_loss_pct=stop_loss_pct,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = positions.shift(1).fillna(0) * daily_ret
    return strat_ret
