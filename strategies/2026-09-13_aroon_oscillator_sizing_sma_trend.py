"""Strategy: SMA200 trend-following gate with continuous Aroon Oscillator
sizing overlay.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per Google SERP synthesis (TrendSpider/StockCharts/IFCM/Investopedia,
browser_exec): Aroon Oscillator (Tushar Chande, 1995) = AroonUp - AroonDown,
where AroonUp = 100 * (window - periods_since_highest_high) / window and
AroonDown = 100 * (window - periods_since_lowest_low) / window, ranging
over [-100, 100]. This repo has 11 prior Aroon-family entries, but every
single one uses the Aroon Oscillator as a binary threshold/crossover ENTRY
signal (e.g. crossing above zero, crossing above 70/30 bands). This
iteration instead uses the Aroon Oscillator's own natural [-100, 100]
bounded scale as a CONTINUOUS SIZING dial on the SMA(200) trend gate: when
Aroon Oscillator is strongly positive (fresh new highs, no recent lows),
scale exposure up toward `leverage_cap`; when it fades toward zero
(momentum weakening even though the SMA(200) gate is still technically
long), scale exposure back down. Structurally distinct from every other
sizing overlay tested elsewhere in this cron trigger (risk-ratio measures,
%B mean-reversion measure) -- Aroon measures RECENCY of extremes, not risk
or price-band position. First Aroon-Oscillator-as-continuous-sizing
strategy in this repo.

Signal logic
------------
- Base directional signal: long-candidate when close > SMA(trend_window).
- Aroon Oscillator over `aroon_window`: AroonUp/AroonDown per the standard
  formula above; oscillator = AroonUp - AroonDown, in [-100, 100].
- Exposure while trend_long: clip(oscillator / aroon_reference, 0,
  leverage_cap) -- i.e. exposure scales up toward leverage_cap as the
  oscillator approaches +100 (fresh highs dominate), and toward 0 as the
  oscillator approaches 0 or goes negative (momentum has faded or reversed
  even while the slower SMA gate is still nominally long).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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


def _aroon_oscillator(close: pd.Series, window: int) -> pd.Series:
    """Aroon Oscillator = AroonUp - AroonDown, range [-100, 100]."""
    def _periods_since_extreme(arr: np.ndarray, is_max: bool) -> np.ndarray:
        n = len(arr)
        out = np.full(n, np.nan)
        for end in range(window, n):
            seg = arr[end - window:end + 1]
            if np.any(np.isnan(seg)):
                continue
            idx = int(np.argmax(seg)) if is_max else int(np.argmin(seg))
            periods_since = window - idx
            out[end] = periods_since
        return out

    values = close.to_numpy(dtype=float)
    periods_since_high = _periods_since_extreme(values, is_max=True)
    periods_since_low = _periods_since_extreme(values, is_max=False)

    aroon_up = 100.0 * (window - periods_since_high) / window
    aroon_down = 100.0 * (window - periods_since_low) / window
    oscillator = aroon_up - aroon_down
    return pd.Series(oscillator, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    aroon_window: int = 25,
    aroon_reference: float = 60.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    oscillator = _aroon_oscillator(close, aroon_window)

    raw_exposure = (oscillator / aroon_reference).astype(float)
    exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap).fillna(0.0)

    position = exposure.where(trend_long.fillna(False), other=0.0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
