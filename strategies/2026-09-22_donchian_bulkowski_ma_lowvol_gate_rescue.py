"""Strategy: Donchian breakout + Bulkowski MA-position filter, RESCUE ATTEMPT
adding an explicit low-realized-vol-regime gate to the entry condition.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-051, the
near-miss this rescues): the base construction (Donchian N-day-high
breakout + Bulkowski's disclosed "yesterday's close below the 9-day SMA"
contrarian pre-breakout filter + SMA(200) uptrend gate, source:
https://thepatternsite.com/MovingAvgs.html) failed the full-sample Sharpe
threshold on its best config (QQQ, Sharpe 0.957 < 1.0) despite passing
every other validator, and the Step 6 grid showed the effect is almost
entirely confined to LOW realized-vol regimes (21/48 low-vol cells passed
vs 2/48 mid-vol, 0/48 high-vol). This iteration adds this repo's
established low-vol-regime-gate construction (per
strategies/2026-09-03_bb_meanrev_qqq_volregime.py, 2026-09-20-140: 20-day
realized vol <= vol_regime_ratio x trailing 252-day median) directly to
the entry condition, restricting trading to the regime slice where the
grid already showed the edge concentrates, in an attempt to lift the
full-sample Sharpe above the 1.0 rescue threshold by avoiding the
high/mid-vol-regime losing trades entirely rather than diluting the
average across all regimes.

No new external source this iteration -- internal-KB rescue attempt only,
per RESEARCH_LOOP.md's allowance for revisiting a near-miss with a
targeted fix rather than requiring a brand-new source for every iteration.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
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
    donchian_window: int = 20,
    ma_filter_window: int = 9,
    trend_sma_window: int = 200,
    max_hold_days: int = 40,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    donchian_high = high.rolling(donchian_window).max().shift(1)
    donchian_low = low.rolling(donchian_window).min().shift(1)

    ma9 = close.rolling(ma_filter_window).mean()
    below_ma9_yesterday = (close.shift(1) < ma9.shift(1))

    trend_sma = close.rolling(trend_sma_window, min_periods=max(20, trend_sma_window // 4)).mean()
    uptrend_gate = close > trend_sma

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = realized_vol <= (vol_median * vol_regime_ratio)

    breakout = close > donchian_high
    entry = breakout & below_ma9_yesterday & uptrend_gate & low_vol_regime
    exit_support = close < donchian_low

    pos_vals = []
    in_pos = False
    hold_count = 0
    for i in range(len(close)):
        if not in_pos and bool(entry.iloc[i]):
            in_pos = True
            hold_count = 0
        elif in_pos:
            hold_count += 1
            if bool(exit_support.iloc[i]) or hold_count >= max_hold_days:
                in_pos = False
        pos_vals.append(1 if in_pos else 0)

    return pd.Series(pos_vals, index=close.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    donchian_window: int = 20,
    ma_filter_window: int = 9,
    trend_sma_window: int = 200,
    max_hold_days: int = 40,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        donchian_window=donchian_window,
        ma_filter_window=ma_filter_window,
        trend_sma_window=trend_sma_window,
        max_hold_days=max_hold_days,
        vol_window=vol_window,
        vol_lookback=vol_lookback,
        vol_regime_ratio=vol_regime_ratio,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = (position.shift(1).fillna(0) * daily_ret).fillna(0.0)
    return strat_ret
