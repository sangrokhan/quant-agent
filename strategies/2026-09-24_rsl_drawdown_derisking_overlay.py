"""Strategy: RSL signal-line crossover (base signal from
2026-09-24_rsl_signal_crossover_trend_gate.py) wrapped with a tiered
drawdown-based de-risking overlay.

Hypothesis (knowledge_base id 2026-09-24-005):
Per https://quantmemo.com/concepts/drawdown-based-derisking-triggers,
drawdown-based de-risking triggers are a general risk-management overlay:
pre-agreed mechanical position-size cuts fire once losses from the
strategy's own peak equity reach specified tiers (e.g. cut to 60% at 1.5x
the backtest's typical drawdown, halt entirely at 2x typical drawdown).
This iteration applies that overlay to this same cron trigger's SPY
near-miss (2026-09-24-001: RSL signal-line crossover trend-gate, SPY
Sharpe 0.710 fails the 1.0 threshold, all other validators pass) to test
whether capping losses during SPY's worst drawdown episodes can lift its
risk-adjusted return above threshold, following this repo's established
de-risking-overlay rescue pattern (e.g. 2026-09-13-030's inverse-vol-
targeting rescue of SuperTrend/SOL).

Mechanism
---------
- Run the base RSL signal-line-crossover position series (identical logic
  to 2026-09-24_rsl_signal_crossover_trend_gate.py).
- Track the strategy's own cumulative-equity running peak and current
  drawdown-from-peak.
- Tier 1 (tier1_dd_pct, default 0.10): once drawdown exceeds this, scale
  exposure to tier1_exposure (default 0.5) until the drawdown recovers
  back above a hysteresis buffer (tier1_dd_pct * recovery_frac).
- Tier 2 (tier2_dd_pct, default 0.18): once drawdown exceeds this, scale
  exposure to tier2_exposure (default 0.0, i.e. flat) until recovery.
- Otherwise: full base-signal exposure (1.0x).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (continuous [0,1] exposure series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _base_rsl_position(
    close: pd.Series,
    rsl_period: int,
    fast_window: int,
    slow_window: int,
    trend_window: int,
    max_hold_days: int,
) -> pd.Series:
    rsl = (close / close.rolling(rsl_period).mean()) * 10.0
    rsl_fast = rsl.rolling(fast_window).mean()
    rsl_slow = rsl.rolling(slow_window).mean()

    trend_sma = close.rolling(trend_window).mean()
    trend_ok = close > trend_sma

    cross_up = (rsl_fast > rsl_slow) & (rsl_fast.shift(1) <= rsl_slow.shift(1))
    cross_down = (rsl_fast < rsl_slow) & (rsl_fast.shift(1) >= rsl_slow.shift(1))

    n = len(close)
    cross_up_arr = cross_up.fillna(False).to_numpy()
    cross_down_arr = cross_down.fillna(False).to_numpy()
    trend_ok_arr = trend_ok.fillna(False).to_numpy()

    pos_arr = [0] * n
    in_pos = False
    hold_days = 0
    for i in range(n):
        if in_pos:
            hold_days += 1
            if cross_down_arr[i] or (not trend_ok_arr[i]) or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
        else:
            if cross_up_arr[i] and trend_ok_arr[i]:
                in_pos = True
                hold_days = 0
        pos_arr[i] = 1 if in_pos else 0

    return pd.Series(pos_arr, index=close.index, dtype=int)


def generate_signals(
    price_df: pd.DataFrame,
    rsl_period: int = 135,
    fast_window: int = 8,
    slow_window: int = 30,
    trend_window: int = 100,
    max_hold_days: int = 20,
    tier1_dd_pct: float = 0.10,
    tier1_exposure: float = 0.5,
    tier2_dd_pct: float = 0.18,
    tier2_exposure: float = 0.0,
    recovery_frac: float = 0.5,
) -> pd.Series:
    """Return a continuous [0,1] exposure series (base RSL signal * de-risking multiplier)."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    base_position = _base_rsl_position(
        close, rsl_period, fast_window, slow_window, trend_window, max_hold_days
    )
    daily_ret = close.pct_change().fillna(0.0)
    base_strat_ret = base_position.shift(1).fillna(0).astype(float) * daily_ret

    ret_arr = base_strat_ret.to_numpy()
    pos_arr = base_position.to_numpy()

    exposure = [1.0] * n
    equity = 1.0
    peak = 1.0
    tier = 0  # 0 = full, 1 = tier1, 2 = tier2

    for i in range(n):
        # apply the previous day's exposure multiplier to compute today's equity update
        mult = tier1_exposure if tier == 1 else (tier2_exposure if tier == 2 else 1.0)
        equity *= (1.0 + mult * ret_arr[i])
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0

        if tier == 0:
            if dd >= tier2_dd_pct:
                tier = 2
            elif dd >= tier1_dd_pct:
                tier = 1
        elif tier == 1:
            if dd >= tier2_dd_pct:
                tier = 2
            elif dd <= tier1_dd_pct * recovery_frac:
                tier = 0
        elif tier == 2:
            if dd <= tier1_dd_pct * recovery_frac:
                tier = 0
            elif dd <= tier2_dd_pct:
                tier = 1

        next_mult = tier1_exposure if tier == 1 else (tier2_exposure if tier == 2 else 1.0)
        exposure[i] = pos_arr[i] * next_mult

    return pd.Series(exposure, index=close.index, dtype=float)


def generate_returns(
    price_df: pd.DataFrame,
    rsl_period: int = 135,
    fast_window: int = 8,
    slow_window: int = 30,
    trend_window: int = 100,
    max_hold_days: int = 20,
    tier1_dd_pct: float = 0.10,
    tier1_exposure: float = 0.5,
    tier2_dd_pct: float = 0.18,
    tier2_exposure: float = 0.0,
    recovery_frac: float = 0.5,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        rsl_period=rsl_period, fast_window=fast_window, slow_window=slow_window,
        trend_window=trend_window, max_hold_days=max_hold_days,
        tier1_dd_pct=tier1_dd_pct, tier1_exposure=tier1_exposure,
        tier2_dd_pct=tier2_dd_pct, tier2_exposure=tier2_exposure,
        recovery_frac=recovery_frac,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
