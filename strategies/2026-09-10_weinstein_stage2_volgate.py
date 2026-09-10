"""Strategy: Weinstein Stage 2 breakout, gated by a low-volatility regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-128):
Direct fix attempt for this cron trigger's near-miss 2026-09-10-127 (plain
Weinstein Stage 2 breakout: full-sample Sharpe failed on both QQQ (0.679)
and SPY (0.700), despite MDD/TC/walk-forward/param-sensitivity all passing
cleanly). That iteration's own grid `by_vol_regime` breakdown showed the
edge was concentrated almost entirely in the low-vol tercile (low 36/72=0.50
vs mid 7/72=0.097 vs high 0/72=0.0), with a best-cell Sharpe of 2.81 in the
low-vol regime alone.

Per https://pyquantlab.medium.com/an-algorithmic-exploration-of-a-trend-following-strategy-with-regime-filter-and-dynamic-stops-70a7c6d41134
(visited this iteration): "Trend-following strategies are most effective
when a clear trend is present... requiring [a volatility filter] attempts
to trade only when the market is clearly trending" -- generic corroboration
that trend-following systems benefit from an explicit volatility regime
gate, matching this repo's own established pattern (identical construction
to the already-accepted 2026-09-03_bb_meanrev_qqq_volregime.py: 20d realized
vol vs its trailing 252d median).

Operationalized rule: identical entry/exit mechanics to 2026-09-10-127
(Stage 2 regime = close>SMA AND SMA rising; entry = breakout above rolling
N-day high while in that regime; exit = close<SMA, SMA flat/falling, or
time-stop) PLUS an additional AND-gate on entry: 20-day realized volatility
must be <= its trailing 252-day median (low-vol regime only).
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


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 100,
    sma_slope_lookback: int = 20,
    breakout_window: int = 50,
    max_hold_days: int = 60,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(sma_window).mean()
    sma_rising = sma > sma.shift(sma_slope_lookback)
    stage2_regime = (close > sma) & sma_rising.fillna(False)

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = realized_vol <= (vol_median_1y * vol_regime_ratio)

    rolling_high = close.rolling(breakout_window).max().shift(1)
    breakout = close > rolling_high

    entry = breakout & stage2_regime & low_vol_regime.fillna(False)
    exit_below_sma = close < sma
    exit_sma_flat_or_falling = ~sma_rising.fillna(False)
    exit_regime_flip = ~low_vol_regime.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if (
                bool(exit_below_sma.iloc[i])
                or bool(exit_sma_flat_or_falling.iloc[i])
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
