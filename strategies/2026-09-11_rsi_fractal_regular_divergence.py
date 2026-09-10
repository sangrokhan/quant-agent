"""Strategy: RSI regular bullish divergence via matched price/RSI fractal swings.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-021):
Per https://secuora.net/strategy/rsi-divergence (visited this iteration):
regular bullish RSI divergence is defined mechanically as (1) confirmed
3-bar fractal SWING LOWS on both the price series and the RSI(14) series
independently, (2) the most recent confirmed price swing low is LOWER than
the prior confirmed price swing low, while the RSI value at that same swing
is HIGHER than the RSI value at the prior swing low -- i.e. price makes a
fresh low but momentum does not confirm it. Entry is at the close of the
candle that confirms the second (divergent) swing (3 bars after the swing
low, per the fractal-confirmation rule -- no look-ahead). Exit uses a fixed
target/stop framework: stop beyond the price extreme of the divergence,
target at a configurable risk-multiple (source uses 2R), with a max_hold
time-stop as a safety net since the source's own backtest was never
published (their engine lacks the primitive) -- this repo supplies its own
mechanical implementation and tests it independently on daily bars.

Novelty vs existing repo entries: distinct from Wilder's RSI Failure Swing
(2026-09-10-102, a single-oscillator-only pattern with no price-swing
matching) and distinct from Turtle Soup / SFP / Island Reversal (all
price-only patterns) -- this is the first strategy in this repo that
requires a divergent match between two independently-computed swing series
(price AND an oscillator), which is the defining mechanical feature of
"divergence" as a technique family.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50.0)
    return rsi


def _fractal_swing_lows(series: pd.Series, lookback: int) -> pd.Series:
    """Confirmed fractal swing-low index: series[i] is a swing low if it is
    the minimum within [i-lookback, i+lookback], confirmed only once the
    `lookback` bars AFTER i have closed (no look-ahead: the confirmation
    itself is only known at i+lookback)."""
    n = len(series)
    is_low = pd.Series(False, index=series.index)
    vals = series.values
    for i in range(lookback, n - lookback):
        window = vals[i - lookback : i + lookback + 1]
        center = vals[i]
        if np.isnan(center):
            continue
        if center == np.nanmin(window) and np.sum(window == center) == 1:
            is_low.iloc[i] = True
    return is_low


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    fractal_lookback: int = 3,
    stop_atr_mult: float = 1.5,
    atr_period: int = 14,
    reward_r_multiple: float = 2.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: at the confirmation bar (swing_idx + fractal_lookback) of a
    fresh price swing low that is LOWER than the prior confirmed swing low
    while RSI at the same swing is HIGHER than RSI at the prior swing low
    (regular bullish divergence). Exit: stop below the divergence's price
    extreme (entry_low - stop_atr_mult*ATR), target reward_r_multiple*R
    above entry, or max_hold_days time-stop, whichever comes first.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close
    n = len(close)

    rsi = _rsi(close, rsi_period)

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    atr = tr.rolling(atr_period).mean()

    swing_low_mask = _fractal_swing_lows(low, fractal_lookback)
    swing_idxs = list(np.where(swing_low_mask.values)[0])

    position = pd.Series(0, index=close.index, dtype=int)

    in_position = False
    entry_i = None
    stop_level = None
    target_level = None

    # Map each confirmed swing low to its confirmation bar (swing_i + lookback)
    confirmations = []  # (confirmation_bar_idx, swing_idx)
    for si in swing_idxs:
        conf_i = si + fractal_lookback
        if conf_i < n:
            confirmations.append((conf_i, si))
    confirmations.sort()

    prior_swing_i = None
    conf_pointer = 0

    for i in range(n):
        # process any confirmations that land on this bar
        while conf_pointer < len(confirmations) and confirmations[conf_pointer][0] == i:
            conf_i, si = confirmations[conf_pointer]
            conf_pointer += 1
            if prior_swing_i is not None and not in_position:
                price_low_now = low.iloc[si]
                price_low_prev = low.iloc[prior_swing_i]
                rsi_now = rsi.iloc[si]
                rsi_prev = rsi.iloc[prior_swing_i]
                if (
                    pd.notna(price_low_now)
                    and pd.notna(price_low_prev)
                    and pd.notna(rsi_now)
                    and pd.notna(rsi_prev)
                    and price_low_now < price_low_prev
                    and rsi_now > rsi_prev
                ):
                    entry_price = close.iloc[i]
                    atr_i = atr.iloc[i]
                    risk = (
                        stop_atr_mult * atr_i
                        if pd.notna(atr_i)
                        else max(entry_price - price_low_now, 1e-6)
                    )
                    stop_level = price_low_now - (stop_atr_mult * atr_i if pd.notna(atr_i) else 0.0)
                    stop_dist = entry_price - stop_level
                    if stop_dist <= 0:
                        stop_dist = risk
                        stop_level = entry_price - stop_dist
                    target_level = entry_price + reward_r_multiple * stop_dist
                    in_position = True
                    entry_i = i
            prior_swing_i = si

        if in_position:
            position.iloc[i] = 1
            price = close.iloc[i]
            hold_len = i - entry_i
            if (
                price <= stop_level
                or price >= target_level
                or hold_len >= max_hold_days
            ):
                in_position = False
                entry_i = None
                stop_level = None
                target_level = None

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
