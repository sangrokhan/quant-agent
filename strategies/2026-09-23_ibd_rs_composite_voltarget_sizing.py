"""Strategy: IBD-style weighted RS composite momentum + inverse-vol sizing overlay.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Direct rescue attempt for this same cron trigger's own near-miss rejection
2026-09-23-138 (IBD weighted RS composite: 0.4*ret(63d)+0.2*ret(126d)+
0.2*ret(189d)+0.2*ret(252d), binary long/flat). That entry's own notes
flagged: "QQQ fails max_drawdown decisively (0.341 vs 0.25) despite passing
4/5 validators cleanly... a volatility-targeting/leverage-cap overlay
specifically addressing QQQ's MDD failure (similar to prior
leverage_cap_aware_design entries) could rescue this family without
changing the core signal."

This iteration keeps the exact same underlying entry/exit signal (weighted
RS composite crossing entry_threshold/exit_threshold, same as 2026-09-23-138)
but replaces the fixed full-size {0,1} position with a continuous
inverse-realized-volatility-scaled exposure (same overlay technique used
successfully elsewhere in this repo, e.g.
strategies/2026-09-08_vol_targeting_trend_overlay.py): whenever the RS
composite signal wants to be long, size the position as
min(target_vol / realized_vol, leverage_cap) instead of always 1.0. This
directly targets the documented MDD failure mode (QQQ's worst drawdowns
occurred during genuinely high-realized-vol regimes where the binary
full-size position was most exposed) while leaving the core RS-momentum
timing signal completely unchanged, isolating whether SIZING (not entry
timing) rescues the QQQ near-miss.

Signal logic
------------
- Same weighted_rs composite as 2026-09-23-138:
  weighted_rs = 0.4*ret(63d) + 0.2*ret(126d) + 0.2*ret(189d) + 0.2*ret(252d)
- Same entry/exit/max_hold_days state machine as 2026-09-23-138 to decide
  WHEN to be long vs flat.
- NEW: while the state machine says "long", scale exposure as
  min(target_vol / realized_vol(vol_window), leverage_cap) instead of a
  fixed 1.0, using only trailing (non-lookahead) realized volatility.
- Exposure is 0 whenever the state machine says flat.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        generate_signals returns a *continuous* exposure series in
        [0, leverage_cap] (not strictly {0,1}), since the sizing mechanism
        itself is under test here.
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


def _weighted_rs(close: pd.Series, w3: int = 63, w6: int = 126, w9: int = 189, w12: int = 252) -> pd.Series:
    r3 = close / close.shift(w3) - 1.0
    r6 = close / close.shift(w6) - 1.0
    r9 = close / close.shift(w9) - 1.0
    r12 = close / close.shift(w12) - 1.0
    return 0.4 * r3 + 0.2 * r6 + 0.2 * r9 + 0.2 * r12


def _realized_vol(close: pd.Series, vol_window: int) -> pd.Series:
    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    return daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)


def _long_flag(
    close: pd.Series,
    w3: int,
    w6: int,
    w9: int,
    w12: int,
    entry_threshold: float,
    exit_threshold: float,
    max_hold_days: int,
) -> pd.Series:
    weighted_rs = _weighted_rs(close, w3, w6, w9, w12)

    in_pos_series = pd.Series(False, index=close.index)
    in_pos = False
    hold_days = 0
    for i in range(len(close)):
        rs = weighted_rs.iloc[i]
        if pd.isna(rs):
            in_pos_series.iloc[i] = in_pos
            if in_pos:
                hold_days += 1
            continue
        if not in_pos:
            if rs > entry_threshold:
                in_pos = True
                hold_days = 0
        else:
            hold_days += 1
            if rs < exit_threshold or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
        in_pos_series.iloc[i] = in_pos

    return in_pos_series


def generate_signals(
    price_df: pd.DataFrame,
    w3: int = 63,
    w6: int = 126,
    w9: int = 189,
    w12: int = 252,
    entry_threshold: float = 0.0,
    exit_threshold: float = -0.05,
    max_hold_days: int = 60,
    vol_window: int = 20,
    target_vol: float = 0.15,
    leverage_cap: float = 1.0,
    rebalance_deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous target-exposure series in [0, leverage_cap].

    ``rebalance_deadband`` (fraction of leverage_cap) suppresses re-sizing
    unless the target exposure has drifted from the currently-HELD exposure
    by more than this much -- this bounds daily rebalancing turnover (and
    the transaction-cost drag it causes) while still tracking large
    volatility-regime shifts, using the same rebalance-buffer technique
    already validated elsewhere in this repo (e.g. many "continuous sizing
    dial" entries in knowledge_base/strategies_log.jsonl).
    """
    df = _prep(price_df)
    close = df["close"]

    long_flag = _long_flag(close, w3, w6, w9, w12, entry_threshold, exit_threshold, max_hold_days)

    realized_vol = _realized_vol(close, vol_window)
    safe_vol = realized_vol.clip(lower=1e-4)
    raw_exposure = (target_vol / safe_vol).clip(upper=leverage_cap)

    target = raw_exposure.where(long_flag, other=0.0).fillna(0.0)

    deadband_abs = rebalance_deadband * leverage_cap
    held = pd.Series(0.0, index=target.index)
    current = 0.0
    for i in range(len(target)):
        t = target.iloc[i]
        if abs(t - current) > deadband_abs:
            current = t
        held.iloc[i] = current

    return held


def generate_returns(
    price_df: pd.DataFrame,
    w3: int = 63,
    w6: int = 126,
    w9: int = 189,
    w12: int = 252,
    entry_threshold: float = 0.0,
    exit_threshold: float = -0.05,
    max_hold_days: int = 60,
    vol_window: int = 20,
    target_vol: float = 0.15,
    leverage_cap: float = 1.0,
    rebalance_deadband: float = 0.15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    exposure = generate_signals(
        price_df,
        w3=w3, w6=w6, w9=w9, w12=w12,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        max_hold_days=max_hold_days,
        vol_window=vol_window,
        target_vol=target_vol,
        leverage_cap=leverage_cap,
        rebalance_deadband=rebalance_deadband,
    )

    daily_ret = close.pct_change()
    # Exposure at t-1 determines return realized at t (avoid lookahead).
    strat_ret = daily_ret * exposure.shift(1).fillna(0.0)
    return strat_ret.fillna(0.0)
