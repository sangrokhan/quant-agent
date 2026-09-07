"""Strategy: Vertical Horizontal Filter (VHF) regime gate + Donchian breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-057):
Per trendsandbreakouts.com's "Vertical Horizontal Filter - Settings and
Trading Rules" (Adam White's VHF, a trend-efficiency ratio comparing net
directional distance to total path traveled over a lookback window): VHF
rising from a low level identifies genuinely trend-friendly regimes, while
low/falling VHF marks choppy/rotational conditions where breakout systems
whipsaw. The article's own "practical rule" is: only take trend-following
breakout trades when price is above a rising baseline (here, an SMA) AND VHF
is rising from a relatively low area; a Donchian channel or Supertrend
supplies the actual trigger. This strategy operationalizes that exact
combination -- VHF regime gate + SMA trend baseline + Donchian breakout
trigger -- distinct from this repo's prior *ungated* Donchian variants
(2026-09-03-008 with a plain 200-SMA filter, 2026-09-04-054 asymmetric-window
Turtle rule) which never used a trend-EFFICIENCY gate, only a trend-
DIRECTION gate. First VHF-based construction in this repo.

Signal logic
------------
- VHF(n) = (max(close, n) - min(close, n)) / sum(|close_i - close_i-1|, n)
  -- Adam White's original formula.
- Trend-efficiency gate: VHF(vhf_period) >= vhf_threshold AND VHF is rising
  (VHF > VHF shifted by vhf_slope_lookback bars).
- Trend-direction baseline: close > SMA(trend_window) (rising baseline
  approximated by requiring the SMA itself to have a positive slope over
  trend_window // 4 bars, per the source's "rising baseline" wording).
- Entry (long): VHF gate passes AND baseline condition passes AND close
  breaks above its own rolling donchian_window-day high (the breakout
  trigger the source explicitly delegates to a channel/breakout tool).
- Exit: close falls below the rolling donchian_exit_window-day low (Turtle-
  style asymmetric trailing exit), OR VHF regime gate fails (efficiency
  collapses -- source's own guidance that a durable trend needs VHF support),
  OR after max_hold_days trading days.
- Flat (no position) otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _vhf(close: pd.Series, n: int) -> pd.Series:
    highest = close.rolling(n).max()
    lowest = close.rolling(n).min()
    numerator = highest - lowest
    denominator = close.diff().abs().rolling(n).sum()
    return numerator / denominator.replace(0.0, pd.NA)


def generate_signals(
    price_df: pd.DataFrame,
    vhf_period: int = 28,
    vhf_threshold: float = 0.35,
    vhf_slope_lookback: int = 5,
    trend_window: int = 50,
    donchian_window: int = 20,
    donchian_exit_window: int = 10,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    vhf = _vhf(close, vhf_period)
    vhf_rising = vhf > vhf.shift(vhf_slope_lookback)
    vhf_gate = (vhf >= vhf_threshold) & vhf_rising

    sma = close.rolling(trend_window).mean()
    sma_slope_lb = max(trend_window // 4, 1)
    sma_rising = sma > sma.shift(sma_slope_lb)
    baseline_ok = (close > sma) & sma_rising

    donchian_high = close.rolling(donchian_window).max().shift(1)
    donchian_low = close.rolling(donchian_exit_window).min().shift(1)

    entry = vhf_gate & baseline_ok & (close > donchian_high)
    exit_breakdown = close < donchian_low
    exit_regime_fail = ~vhf_gate

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_breakdown.iloc[i]) or bool(exit_regime_fail.iloc[i]) or held >= max_hold_days:
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
