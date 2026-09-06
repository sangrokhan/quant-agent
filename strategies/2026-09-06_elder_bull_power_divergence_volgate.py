"""Strategy: Elder-Ray Bull Power bullish divergence, regime-gated (mid/high vol).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-176):
Direct follow-up to near-miss 2026-09-06-135 (plain Elder-Ray Bull Power
bullish divergence, rejected -- full-sample Sharpe 0.882/0.460 missed
threshold on QQQ/SPY, but that iteration's own notes flagged it as a
NEAR-MISS worth revisiting because its Step-6 grid pass_fraction (0.160,
23/144) was unusually EVENLY spread across all three realized-vol terciles
(6/8/9 of 48 passes in low/mid/high respectively) rather than concentrated
in one regime -- suggesting a genuine but regime-dependent edge that an
unconditional entry rule dilutes with false signals in the wrong regime).
This iteration adds an explicit realized-volatility regime gate: only take
entries when the 20-day realized vol is AT OR ABOVE its trailing 1-year
median (i.e. restrict trading to the mid/high-vol terciles, mirroring this
repo's own convention from strategies/2026-09-03_bb_meanrev_qqq_volregime.py
but inverted -- divergence-based reversal entries plausibly need genuine
volatility/dislocation to be meaningful, unlike that strategy's low-vol-only
mean-reversion premise), while keeping the identical divergence-detection
and entry/exit logic from 2026-09-06-135 to isolate whether the regime gate
alone rescues the near-miss.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series {0,1} long/flat
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


def _confirmed_swing_lows(series: pd.Series, window: int) -> pd.Series:
    roll_min = series.rolling(2 * window + 1, center=True, min_periods=2 * window + 1).min()
    is_low = (series == roll_min)
    return is_low.shift(window).fillna(False)


def _mid_high_vol_regime(
    close: pd.Series, vol_window: int = 20, vol_lookback: int = 252, vol_regime_ratio: float = 1.0
) -> pd.Series:
    """True when current realized vol >= its trailing 1yr median (mid/high tercile)."""
    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    return (realized_vol >= (vol_median_1y * vol_regime_ratio)).fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 13,
    swing_window: int = 5,
    max_swing_gap: int = 40,
    max_hold_days: int = 15,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
    require_mid_high_vol: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    ema = close.ewm(span=ema_window, min_periods=ema_window, adjust=False).mean()
    bull_power = high - ema

    price_swing_low = _confirmed_swing_lows(low, swing_window)

    mid_high_vol = _mid_high_vol_regime(
        close, vol_window=vol_window, vol_lookback=vol_lookback, vol_regime_ratio=vol_regime_ratio
    )

    idx = df.index
    n = len(idx)

    pos = pd.Series(0, index=idx, dtype=int)
    in_pos = False
    entry_idx = None

    state = "SEEK_SWING1"
    swing1_idx = None
    swing1_low = None
    swing1_bp = None
    divergence_confirmed_idx = None

    for i in range(n):
        bp = bull_power.iloc[i]
        lo = low.iloc[i]

        if in_pos:
            days_held = i - entry_idx
            hit_time = days_held >= max_hold_days
            hit_bp_exit = bp < 0
            if hit_time or hit_bp_exit:
                in_pos = False
            else:
                pos.iloc[i] = 1
                continue

        if state == "SEEK_SWING1":
            if bool(price_swing_low.iloc[i]):
                swing1_idx, swing1_low, swing1_bp = i, lo, bp
                state = "SEEK_SWING2"
        elif state == "SEEK_SWING2":
            if i - swing1_idx > max_swing_gap:
                if bool(price_swing_low.iloc[i]):
                    swing1_idx, swing1_low, swing1_bp = i, lo, bp
                else:
                    state = "SEEK_SWING1"
            elif bool(price_swing_low.iloc[i]):
                if lo < swing1_low and bp > swing1_bp:
                    divergence_confirmed_idx = i
                    state = "WAIT_BP_CROSS"
                else:
                    swing1_idx, swing1_low, swing1_bp = i, lo, bp
        elif state == "WAIT_BP_CROSS":
            if bp > 0:
                regime_ok = (not require_mid_high_vol) or bool(mid_high_vol.iloc[i])
                if regime_ok:
                    in_pos = True
                    entry_idx = i
                    pos.iloc[i] = 1
                state = "SEEK_SWING1"
                swing1_idx = swing1_low = swing1_bp = None
                divergence_confirmed_idx = None
            elif i - divergence_confirmed_idx > max_swing_gap:
                state = "SEEK_SWING1"
                swing1_idx = swing1_low = swing1_bp = None
                divergence_confirmed_idx = None

    return pos


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret
