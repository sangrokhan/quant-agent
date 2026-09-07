"""Strategy: MACD Histogram bullish divergence, long-only entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-085),
sourced from https://pinescriptforge.com/strategy/macd-histogram-divergence
("MACD Histogram Divergence" strategy). Concrete rules quoted from the source:

    "Enter long on bullish divergence (lower low in price, higher low in
    histogram)."
    "Target the prior swing high (bullish). Stop above/below the
    divergence high/low."

I.e. price makes a LOWER swing low while the MACD histogram (MACD line
minus signal line) makes a HIGHER swing low over the same swing -- momentum
secretly building even as price makes a new low. Distinct from every other
MACD-family strategy already tested in this repo (signal-line crossover,
zero-line filter, Impulse System, MACD-V, VW-MACD, mean-reversion
inflection) by targeting the HISTOGRAM specifically as a swing-divergence
oscillator (not the MACD line itself, and not a crossover mechanic) --
"the histogram often provides earlier signals through divergence... before
the crowd sees the standard MACD crossover."

Swing detection: same N-bar centered local-minimum convention used by
strategies/2026-09-03_rsi_bullish_divergence.py. Entry triggers the bar
after a valid bullish divergence is confirmed. Exit at the prior swing high
(source's own target rule) or a max_hold_days time-stop, whichever first
(no stop-loss mechanic re-implemented here -- validators apply cost/
drawdown checks on the resulting return series directly, per this repo's
existing convention).

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


def _macd_hist(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line - signal_line


def _swing_lows(close: pd.Series, swing_window: int = 5) -> pd.Series:
    roll_min = close.rolling(2 * swing_window + 1, center=True).min()
    return close == roll_min


def _swing_highs(close: pd.Series, swing_window: int = 5) -> pd.Series:
    roll_max = close.rolling(2 * swing_window + 1, center=True).max()
    return close == roll_max


def generate_signals(
    price_df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    swing_window: int = 5,
    lookback_bars: int = 40,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Detects bullish MACD-histogram divergence between successive swing
    lows: second (more recent) swing low has LOWER price but HIGHER
    histogram value than the first, within `lookback_bars`. Enters long the
    bar after confirmation. Exits at the most recent prior swing high
    (source's target rule) or after max_hold_days bars, whichever first.
    """
    df = _prep(price_df)
    close = df["close"]
    hist = _macd_hist(close, fast, slow, signal)
    is_low = _swing_lows(close, swing_window)
    is_high = _swing_highs(close, swing_window)

    swing_low_idx = np.where(is_low.fillna(False).values)[0]
    swing_high_idx = np.where(is_high.fillna(False).values)[0]
    n = len(close)
    entries = np.zeros(n, dtype=bool)
    targets = np.full(n, np.nan)

    for j in range(1, len(swing_low_idx)):
        i2 = swing_low_idx[j]
        prior_candidates = [i1 for i1 in swing_low_idx[:j] if i2 - i1 <= lookback_bars]
        if not prior_candidates:
            continue
        i1 = prior_candidates[-1]
        h1, h2 = hist.iloc[i1], hist.iloc[i2]
        px1, px2 = close.iloc[i1], close.iloc[i2]
        if pd.isna(h1) or pd.isna(h2):
            continue
        if px2 < px1 and h2 > h1:
            entry_bar = i2 + 1
            if entry_bar < n:
                # Target: the most recent confirmed swing high before entry.
                prior_highs = swing_high_idx[swing_high_idx < entry_bar]
                if len(prior_highs) > 0:
                    target_price = close.iloc[prior_highs[-1]]
                    if target_price > close.iloc[entry_bar]:
                        entries[entry_bar] = True
                        targets[entry_bar] = target_price

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_bar = -1
    target_price = np.nan
    for t in range(n):
        if entries[t] and not in_pos:
            in_pos = True
            entry_bar = t
            target_price = targets[t]
        if in_pos:
            position[t] = 1
            held = t - entry_bar
            hit_target = (not pd.isna(target_price)) and close.iloc[t] >= target_price
            if hit_target or held >= max_hold_days:
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
