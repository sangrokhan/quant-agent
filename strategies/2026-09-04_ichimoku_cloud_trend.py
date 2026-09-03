"""Strategy: Ichimoku Cloud (Kumo) trend-following with Tenkan/Kijun confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-034):
Per quantifiedstrategies.com's Ichimoku Cloud article: price trading above
the Ichimoku cloud (Kumo, the band between Senkou Span A and Senkou Span B)
indicates an established uptrend; combining this with a Tenkan-sen/Kijun-sen
bullish alignment (Tenkan > Kijun) as a momentum confirmation should filter
out weak/choppy above-cloud periods where price is only marginally above a
thin cloud without underlying momentum. Long-only. The source itself
reports Ichimoku reduces drawdowns but often fails to beat buy-and-hold
across assets -- this is tested here as a falsification/confirmation check
on this repo's equity/crypto universe, similar epistemic status to prior
sources with documented negative priors (Bollinger squeeze -011, Fibonacci
-022).

Standard Ichimoku component formulas (all from the source):
- Tenkan-sen (Conversion Line, tenkan_window periods, standard 9):
  (highest high + lowest low) / 2 over the window.
- Kijun-sen (Base Line, kijun_window periods, standard 26):
  (highest high + lowest low) / 2 over the window.
- Senkou Span A (Leading Span A): (Tenkan + Kijun) / 2, plotted
  `kijun_window` periods AHEAD (i.e. today's cloud edge value was computed
  `kijun_window` bars ago -- shift(kijun_window) to align causally).
- Senkou Span B (Leading Span B, senkou_b_window periods, standard 52):
  (highest high + lowest low) / 2 over the window, also plotted
  `kijun_window` periods ahead.
- Cloud (Kumo) = area between Span A and Span B.

Signal logic
------------
- Entry (long): close > max(Senkou Span A, Senkou Span B) [above cloud]
  AND Tenkan-sen > Kijun-sen (bullish momentum confirmation), evaluated
  causally (both spans and Tenkan/Kijun use only data available as of
  today's bar; the plotted "26-ahead" cloud edges are shifted so their
  value at time t reflects data known at time t - kijun_window, which is
  the correct causal interpretation of "the cloud value in effect today").
- Exit: close < cloud (either close <= Span A or close <= Span B, i.e.
  price no longer above the FULL cloud), OR Tenkan crosses below Kijun.
- Flat otherwise; long-only, no shorting.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    tenkan_window: int = 9,
    kijun_window: int = 26,
    senkou_b_window: int = 52,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    tenkan = (high.rolling(tenkan_window).max() + low.rolling(tenkan_window).min()) / 2.0
    kijun = (high.rolling(kijun_window).max() + low.rolling(kijun_window).min()) / 2.0
    senkou_a_raw = (tenkan + kijun) / 2.0
    senkou_b_raw = (high.rolling(senkou_b_window).max() + low.rolling(senkou_b_window).min()) / 2.0

    # The cloud is plotted `kijun_window` bars ahead of the data it's
    # computed from; to know "the cloud value in effect today" causally,
    # today's displayed cloud edge was computed kijun_window bars ago.
    senkou_a = senkou_a_raw.shift(kijun_window)
    senkou_b = senkou_b_raw.shift(kijun_window)

    cloud_top = pd.concat([senkou_a, senkou_b], axis=1).max(axis=1)
    cloud_bottom = pd.concat([senkou_a, senkou_b], axis=1).min(axis=1)

    above_cloud = close > cloud_top
    below_cloud = close < cloud_bottom
    bullish_confirm = tenkan > kijun
    bearish_cross = (tenkan < kijun) & (tenkan.shift(1) >= kijun.shift(1))

    entry = above_cloud & bullish_confirm
    exit_signal = below_cloud | bearish_cross

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
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
