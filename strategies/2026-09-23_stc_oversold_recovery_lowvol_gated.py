"""Strategy: Schaff Trend Cycle (STC) oversold-recovery long, trend-gated +
low-volatility-regime gate rescue attempt.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-056):
Direct rescue attempt for near-miss/reject 2026-09-23-055 (plain STC
oversold-recovery, trend-gated, full-sample Sharpe 0.558 QQQ / 0.600 SPY,
both < 1.0 threshold). That iteration's own grid (216 cells,
vol_regime_splits=3) showed the edge is real but narrow: pass_fraction 0.245
overall, but by_vol_regime = low 35/72, mid 18/72, **high 0/72** -- the
strategy is decisively wiped out in the high-vol tercile while achieving a
best-cell Sharpe of 2.04 in the low-vol tercile (SPY). This variant adds
this repo's established low-vol-regime-gate construction (identical to
strategies/2026-09-03_bb_meanrev_qqq_volregime.py and 2026-09-20-140: 20-day
realized vol <= vol_regime_ratio x trailing 252-day median) directly to the
entry condition, restricting trading to the regime the grid showed the edge
concentrates in, on top of the same STC oversold-recovery + SMA trend-gate
entry/exit logic otherwise. No new external source consulted this
iteration -- internal-KB rescue attempt only, per RESEARCH_LOOP.md's
guidance that a flagged near-miss is worth revisiting with a targeted tweak
before moving to a brand-new hypothesis.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _compute_stc(
    close: pd.Series,
    fast_window: int = 23,
    slow_window: int = 50,
    stoch_window: int = 10,
    stoch_smooth: int = 3,
) -> pd.Series:
    ema1 = close.ewm(span=fast_window, adjust=False).mean()
    ema2 = close.ewm(span=slow_window, adjust=False).mean()
    macd = ema1 - ema2

    macd_low = macd.rolling(stoch_window).min()
    macd_high = macd.rolling(stoch_window).max()
    denom_k = (macd_high - macd_low).replace(0, pd.NA)
    pct_k = 100 * (macd - macd_low) / denom_k
    pct_k = pct_k.ffill().fillna(50.0)

    pct_d = pct_k.rolling(stoch_smooth).mean()

    stc_raw_low = pct_d.rolling(stoch_window).min()
    stc_raw_high = pct_d.rolling(stoch_window).max()
    denom2 = (stc_raw_high - stc_raw_low).replace(0, pd.NA)
    stc = 100 * (pct_d - stc_raw_low) / denom2
    stc = stc.ffill().fillna(50.0)
    stc = stc.clip(0, 100)
    return stc


def _low_vol_regime(
    close: pd.Series,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    return realized_vol <= (vol_median * vol_regime_ratio)


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 23,
    slow_window: int = 50,
    stoch_window: int = 10,
    stoch_smooth: int = 3,
    stc_entry_level: float = 25.0,
    stc_exit_level: float = 75.0,
    trend_window: int = 200,
    max_hold_days: int = 15,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    stc = _compute_stc(close, fast_window, slow_window, stoch_window, stoch_smooth)
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma
    low_vol = _low_vol_regime(close, vol_window, vol_lookback, vol_regime_ratio)

    entry = (
        (stc > stc_entry_level)
        & (stc.shift(1) <= stc_entry_level)
        & uptrend.fillna(False)
        & low_vol.fillna(False)
    )
    exit_overbought = (stc < stc_exit_level) & (stc.shift(1) >= stc_exit_level)
    exit_trend_break = ~uptrend.fillna(False)
    exit_regime_flip = ~low_vol.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if (
                bool(exit_overbought.iloc[i])
                or bool(exit_trend_break.iloc[i])
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
