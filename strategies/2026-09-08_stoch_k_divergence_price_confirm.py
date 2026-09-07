"""Strategy: Classic Stochastic %K bullish divergence with price-confirmation trigger.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-083),
sourced from https://www.luxalgo.com/blog/ultimate-guide-to-stochastic-divergence-trading/
("Ultimate Guide to Stochastic Divergence Trading"). Concrete rules quoted
from the source:

    "Regular bullish [divergence]: Lower low [price] / Higher low
    [oscillator] -- Downward momentum may be weakening"

    The source stresses the signal is only "known" once a price
    CONFIRMATION level (defined at the time of the second swing low, not
    with hindsight) is subsequently closed above: "Price later closes above
    the predefined $101 confirmation level -> The candidate has met that
    price-confirmation rule."

I.e. classic Stochastic %K bullish divergence: price makes a LOWER swing
low while %K makes a HIGHER swing low over the same swing, THEN price must
subsequently close above a pre-defined confirmation level (the high of the
bar immediately preceding the second swing low, in this implementation) --
distinct from every OTHER divergence strategy already tested in this repo
(RSI/OBV/ADX/CMF/Force-Index/MFI/%B/KST/A-D-Line/TRIX/RVI divergence) by
using the classic Stochastic %K oscillator AND requiring an explicit
price-confirmation trigger rather than entering on the divergence pattern
alone (the source's key methodological point: "the signal exists when it
becomes known").

Swing detection: same N-bar centered local-minimum convention already used
by strategies/2026-09-03_rsi_bullish_divergence.py (a low is a "swing low"
if it is the minimum close over a centered window).

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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


def _stochastic_k(
    high: pd.Series, low: pd.Series, close: pd.Series, k_window: int = 14, k_smooth: int = 3
) -> pd.Series:
    """Standard %K: smoothed range-position of close within the rolling high/low range."""
    lowest_low = low.rolling(k_window).min()
    highest_high = high.rolling(k_window).max()
    raw_k = 100.0 * (close - lowest_low) / (highest_high - lowest_low).replace(0.0, pd.NA)
    k = raw_k.rolling(k_smooth).mean()
    return k


def _swing_lows(close: pd.Series, swing_window: int = 5) -> pd.Series:
    """Boolean mask: True where `close` is the min over a centered window
    of width (2*swing_window+1)."""
    roll_min = close.rolling(2 * swing_window + 1, center=True).min()
    return close == roll_min


def generate_signals(
    price_df: pd.DataFrame,
    k_window: int = 14,
    k_smooth: int = 3,
    swing_window: int = 5,
    lookback_bars: int = 40,
    confirm_window: int = 10,
    exit_k_level: float = 80.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Detects regular bullish Stochastic %K divergence between successive
    swing lows: second (more recent) swing low has LOWER price but HIGHER
    %K than the first, within `lookback_bars`. The confirmation level is
    the highest high of the `confirm_window` bars immediately preceding the
    second swing low; entry triggers the first bar (within confirm_window
    bars after the divergence) that price closes above that level. Exits
    when %K crosses above exit_k_level (momentum normalized/overbought) or
    after max_hold_days bars, whichever first.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close
    k = _stochastic_k(high, low, close, k_window, k_smooth)
    is_low = _swing_lows(close, swing_window)

    swing_idx = np.where(is_low.fillna(False).values)[0]
    n = len(close)
    entries = np.zeros(n, dtype=bool)

    for j in range(1, len(swing_idx)):
        i2 = swing_idx[j]
        prior_candidates = [i1 for i1 in swing_idx[:j] if i2 - i1 <= lookback_bars]
        if not prior_candidates:
            continue
        i1 = prior_candidates[-1]
        k1, k2 = k.iloc[i1], k.iloc[i2]
        px1, px2 = close.iloc[i1], close.iloc[i2]
        if pd.isna(k1) or pd.isna(k2):
            continue
        if px2 < px1 and k2 > k1:
            # Bullish divergence candidate confirmed at swing low i2.
            # Confirmation level: highest high of the confirm_window bars
            # immediately preceding i2 (defined BEFORE we look for the
            # trigger, avoiding hindsight bias per the source's own point).
            win_start = max(0, i2 - confirm_window)
            confirm_level = high.iloc[win_start:i2].max()
            if pd.isna(confirm_level):
                continue
            # Look for the first bar within confirm_window bars AFTER i2
            # where close breaks above confirm_level.
            for t in range(i2 + 1, min(i2 + 1 + confirm_window, n)):
                if close.iloc[t] > confirm_level:
                    entries[t] = True
                    break

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_bar = -1
    for t in range(n):
        if entries[t] and not in_pos:
            in_pos = True
            entry_bar = t
        if in_pos:
            position[t] = 1
            held = t - entry_bar
            k_t = k.iloc[t]
            if (not pd.isna(k_t) and k_t > exit_k_level) or held >= max_hold_days:
                in_pos = False

    return pd.Series(position, index=close.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
