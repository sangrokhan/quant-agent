"""Strategy: Ichimoku full 3-condition confluence -- TK cross above the
cloud, confirmed by the Chikou Span -- long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-085):
Per multiple convergent Ichimoku strategy guides (SnapPChart, AlgoKing,
ChartingLens, via Google search): "In practice, most traders use three: the
TK cross for timing, the Kumo breakout for the trend regime, and the
Chikou span as a filter... A high-probability setup requires confluence:
the cross should be on the correct side of the Kumo, and the Chikou Span
must confirm." / "A bullish signal is confirmed when the Chikou Span is
above the price action it overlaps from 26 periods ago." This is the full
3-condition confluence system, distinct from both prior Ichimoku strategies
in this repo: 2026-09-04-034 used only close>cloud + TK cross (no Chikou
confirmation at all, near-miss rejected); 2026-09-05-049 used only the Kumo
breakout alone (no TK cross, no Chikou). Adding the Chikou Span as a third
independent confirmation is a deliberate attempt to filter out the weaker
signals that made the 2-condition variant a near-miss.

Signal logic
------------
- Tenkan-sen: midpoint of highest-high/lowest-low over tenkan_window bars
  (9).
- Kijun-sen: midpoint of highest-high/lowest-low over kijun_window bars
  (26).
- Senkou Span A/B and the Kumo (cloud) bounds, displaced forward
  `displacement` bars (26), as in 2026-09-05-049.
- Chikou Span: today's close, compared against the close from
  `displacement` bars ago (i.e. Chikou "above price action from 26 periods
  ago" means close[t] > close[t - displacement]).
- Entry (long): (1) Tenkan crosses above Kijun (TK cross) AND (2) close is
  already above the Kumo (upper cloud boundary) at that bar AND (3) close
  > close shifted back `displacement` bars (Chikou confirmation) -- all
  three conditions simultaneously.
- Exit: Tenkan crosses back below Kijun (TK cross reverses), OR close falls
  below the Kumo, OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract (RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _midpoint(high: pd.Series, low: pd.Series, window: int) -> pd.Series:
    return (high.rolling(window).max() + low.rolling(window).min()) / 2.0


def generate_signals(
    price_df: pd.DataFrame,
    tenkan_window: int = 9,
    kijun_window: int = 26,
    senkou_b_window: int = 52,
    displacement: int = 26,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    tenkan = _midpoint(high, low, tenkan_window)
    kijun = _midpoint(high, low, kijun_window)

    senkou_a = ((tenkan + kijun) / 2.0).shift(displacement)
    senkou_b = _midpoint(high, low, senkou_b_window).shift(displacement)

    kumo_upper = pd.concat([senkou_a, senkou_b], axis=1).max(axis=1)
    kumo_lower = pd.concat([senkou_a, senkou_b], axis=1).min(axis=1)

    tk_bull_cross = (tenkan > kijun) & (tenkan.shift(1) <= kijun.shift(1))
    tk_bear_cross = (tenkan < kijun) & (tenkan.shift(1) >= kijun.shift(1))

    above_cloud = close > kumo_upper
    below_cloud = close < kumo_lower

    chikou_confirm = close > close.shift(displacement)

    entry = (
        tk_bull_cross.fillna(False)
        & above_cloud.fillna(False)
        & chikou_confirm.fillna(False)
    )

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    entry_vals = entry.to_numpy()
    tk_bear_vals = tk_bear_cross.fillna(False).to_numpy()
    below_cloud_vals = below_cloud.fillna(False).to_numpy()

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(tk_bear_vals[i]) or bool(below_cloud_vals[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
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
