"""Strategy: RSI bullish divergence, long-only entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-019),
sourced from https://backtestx.in/guide/backtesting-rsi (BacktestX "RSI
Divergence Strategy & Backtesting Guide"). Concrete codified entry rules
quoted from the source:

    1. "RSI must be in oversold (below 30) or overbought (above 70)
       territory during the first swing peak."
    2. "Price must make a clear second peak/trough outside the previous
       boundaries."
    3. "RSI second peak must be visually higher (for bullish) or lower
       (for bearish) than the first."

I.e. bullish RSI divergence: price makes a LOWER swing low while RSI(14)
makes a HIGHER swing low than its own prior swing low, with the first swing
low occurring while RSI was in oversold territory (<30) -- interpreted as
seller momentum exhausting despite price still falling, a classic
momentum-divergence reversal signal. The source's own reported backtest
(major FX pairs, 5yr window) found ~48-52% win rate in range-bound markets
but <35% in strong trends, and recommends filtering divergence entries by a
higher-timeframe trend/support context -- not implemented here (kept
single-timeframe per this repo's existing swing-detection convention) but
noted as a caveat.

This is the first swing-pivot / local-extrema divergence detector tested in
this repo -- structurally different from every prior RSI-based strategy
(RSI(2) mean-reversion, 2026-09-03-005, uses the raw RSI *level* crossing a
threshold, not a divergence *pattern* between two swing points).

Swing detection: a simple N-bar centered local-minimum detector (a low is a
"swing low" if it is the minimum close over a `swing_window`-bar window
centered on it). Long entry triggers the bar after a valid bullish
divergence is confirmed (second swing low identified, lower in price but
higher in RSI than the first, with the first swing low's RSI < 30). Exit
when RSI(14) crosses back above 50 (momentum has normalized) or after
`max_hold_days` bars, whichever comes first -- no stop-loss/target
mechanics per this repo's existing exposure-based approach (validators
apply cost/drawdown checks on the resulting return series directly, no
strategy re-implements portfolio/stop mechanics itself).

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


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Wilder's RSI (standard exponential smoothing, alpha=1/window)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def _swing_lows(close: pd.Series, swing_window: int = 5) -> pd.Series:
    """Boolean mask: True where `close` is the min over a centered window
    of width (2*swing_window+1)."""
    roll_min = close.rolling(2 * swing_window + 1, center=True).min()
    return close == roll_min


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    swing_window: int = 5,
    oversold_threshold: float = 30.0,
    exit_rsi_level: float = 50.0,
    max_hold_days: int = 15,
    lookback_bars: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Detects bullish RSI divergence between successive swing lows within a
    rolling `lookback_bars` window: first swing low's RSI < oversold_threshold,
    second (more recent) swing low has LOWER price but HIGHER RSI than the
    first. Enters long the bar after confirmation. Exits when RSI crosses
    back above exit_rsi_level or after max_hold_days bars, whichever first.
    """
    df = _prep(price_df)
    close = df["close"]
    rsi = _rsi(close, rsi_window)
    is_low = _swing_lows(close, swing_window)

    swing_idx = np.where(is_low.fillna(False).values)[0]
    n = len(close)
    entries = np.zeros(n, dtype=bool)

    for j in range(1, len(swing_idx)):
        i2 = swing_idx[j]
        # find the most recent prior swing low within lookback_bars
        prior_candidates = [i1 for i1 in swing_idx[:j] if i2 - i1 <= lookback_bars]
        if not prior_candidates:
            continue
        i1 = prior_candidates[-1]
        rsi1, rsi2 = rsi.iloc[i1], rsi.iloc[i2]
        px1, px2 = close.iloc[i1], close.iloc[i2]
        if pd.isna(rsi1) or pd.isna(rsi2):
            continue
        if rsi1 < oversold_threshold and px2 < px1 and rsi2 > rsi1:
            # confirmed bullish divergence at swing low i2; entry next bar
            if i2 + 1 < n:
                entries[i2 + 1] = True

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
            rsi_t = rsi.iloc[t]
            if (not pd.isna(rsi_t) and rsi_t > exit_rsi_level) or held >= max_hold_days:
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
