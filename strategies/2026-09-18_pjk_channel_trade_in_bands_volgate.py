"""Strategy: PJK Channels Rule 3 (trade-in-bands, slope-gated pullback)
+ explicit high-vol regime flat-gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-119):
Direct fix for this same cron trigger's prior rejection 2026-09-18-116
(Kaufman PJK Channels Rule 3, per
https://traders.com/Documentation/FEEDbk_docs/2025/05/TradersTips.html):
the grid there showed the strategy passes broadly in low/mid realized-vol
regimes (16/36 and 14/36 cells respectively) but fails COMPLETELY in the
high-vol tercile (0/36 cells) for both equity and crypto, dragging the
blended full-sample Sharpe below the 1.0 bar despite a genuinely strong
low-vol edge (best cell SPY low-vol Sharpe 2.17). This variant adds an
explicit realized-volatility regime gate: flatten (force position=0)
whenever trailing `vol_window`-day realized volatility exceeds
`vol_regime_ratio` times its own trailing `vol_lookback`-day median,
otherwise defer to the underlying PJK Rule 3 slope-gated pullback logic
unchanged. This is the same vol-gating construction already validated as
an effective near-miss rescue elsewhere in this repo (e.g.
2026-09-18_lower_highs_lower_lows_3day_volgate.py,
2026-09-18_123_pattern_reversal_volgate.py).

Signal logic
------------
Identical PJK Rule 3 channel/slope/zone construction as
strategies/2026-09-18_pjk_channel_trade_in_bands.py, with one addition:
  - Compute trailing `vol_window`-day realized volatility of daily returns
    (std of pct_change, NOT annualized).
  - Compute that volatility series' own trailing `vol_lookback`-day
    rolling median (a slow-moving reference level for "normal" vol).
  - high_vol_flag[t] = realized_vol[t] > vol_regime_ratio * vol_median[t]
  - Position is forced to 0 whenever high_vol_flag is True, REGARDLESS of
    what the underlying PJK Rule 3 state machine says; when high_vol_flag
    clears, the underlying state machine's most recent decision applies
    again (no special re-entry logic -- simple override/gate, same
    approach as the repo's other _volgate strategies).

Interface contract for validators (see validation/validators.py) and
grid_test (see validation/grid_test.py):
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} position series aligned to price_df.index.
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Daily strategy returns (position-weighted, no transaction costs
        applied here).

Tunable params (all keyword args, per RESEARCH_LOOP.md Step 5 contract):
    period (default 50)   -- regression/channel lookback (grid's best avg
                              equity config from the ungated variant).
    zone   (default 0.30) -- inner-zone fraction of band width (ditto).
    vol_window (default 20)     -- realized-vol lookback in bars.
    vol_lookback (default 252)  -- rolling-median-of-vol lookback in bars.
    vol_regime_ratio (default 1.3) -- flatten when vol exceeds this
                                       multiple of its own trailing median.
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


def _rolling_channel(close: pd.Series, period: int):
    n = period
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    x_centered = x - x_mean
    denom = (x_centered ** 2).sum()

    vals = close.to_numpy(dtype=float)
    m = len(vals)
    lin_val = np.full(m, np.nan)
    high_dev = np.full(m, np.nan)
    low_dev = np.full(m, np.nan)
    slope_arr = np.full(m, np.nan)

    for t in range(n - 1, m):
        window = vals[t - n + 1 : t + 1]
        y_mean = window.mean()
        slope = (x_centered * (window - y_mean)).sum() / denom
        intercept = y_mean - slope * x_mean
        fitted = intercept + slope * x
        dev = window - fitted
        lin_val[t] = fitted[-1]
        high_dev[t] = max(dev.max(), 0.0)
        low_dev[t] = min(dev.min(), 0.0)
        slope_arr[t] = slope

    return (
        pd.Series(lin_val, index=close.index),
        pd.Series(high_dev, index=close.index),
        pd.Series(low_dev, index=close.index),
        pd.Series(slope_arr, index=close.index),
    )


def _high_vol_flag(
    close: pd.Series,
    vol_window: int,
    vol_lookback: int,
    vol_regime_ratio: float,
) -> pd.Series:
    daily_ret = close.pct_change()
    realized_vol = daily_ret.rolling(vol_window).std()
    vol_median = realized_vol.rolling(vol_lookback, min_periods=max(20, vol_lookback // 4)).median()
    flag = realized_vol > (vol_regime_ratio * vol_median)
    return flag.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 50,
    zone: float = 0.30,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.3,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    lin_val, high_dev, low_dev, slope = _rolling_channel(close, period)
    band_width = high_dev - low_dev
    upperband = lin_val + high_dev
    lowerband = lin_val + low_dev
    long_entry_target = lowerband + zone * band_width
    exit_target = upperband - zone * band_width

    high_vol = _high_vol_flag(close, vol_window, vol_lookback, vol_regime_ratio)

    position = pd.Series(0, index=close.index, dtype=int)
    pos = 0
    for i in range(len(close)):
        if np.isnan(lin_val.iloc[i]):
            position.iloc[i] = 0
            continue
        c = close.iloc[i]
        s = slope.iloc[i]
        if pos == 1:
            if c >= exit_target.iloc[i] or s <= 0:
                pos = 0
        else:
            if s > 0 and c <= long_entry_target.iloc[i]:
                pos = 1

        effective_pos = 0 if bool(high_vol.iloc[i]) else pos
        position.iloc[i] = effective_pos

    return position.fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 50,
    zone: float = 0.30,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.3,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        period=period,
        zone=zone,
        vol_window=vol_window,
        vol_lookback=vol_lookback,
        vol_regime_ratio=vol_regime_ratio,
    )
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
