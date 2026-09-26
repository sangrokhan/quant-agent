"""Strategy: Rolling-window VWAP standard-deviation-band mean reversion,
gated by a trend/chop regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Per HorizonAI's "Build a VWAP Mean Reversion Strategy in Pine Script v6"
(https://www.horizontrading.ai/learn/build-a-vwap-mean-reversion-strategy-in-pine-script-v6,
read via browser_exec since web_extract's ddgs backend cannot extract page
content) and Elev8 Trading's "VWAP Deviation: 2-3 SD Extreme Zones" article
(https://www.elev8-trading.com/education/vwap-deviation), price that
stretches N standard deviations away from its volume-weighted average price
tends to revert back toward VWAP during balanced (non-trending) regimes,
because size-constrained institutional participants judged against VWAP
keep leaning against the extension. The source explicitly warns this fails
on trend days, so this repo's implementation adds an explicit trend/chop
regime gate (ADX-style: ratio of |SMA(fast) - SMA(slow)| to rolling ATR)
rather than trading the raw VWAP-deviation signal unconditionally -- this
repo's data/loaders.py only provides daily OHLCV (no true intraday VWAP
session-anchor), so we adapt the source's per-session VWAP-deviation idea
to a rolling `vwap_window`-day volume-weighted average price with rolling
standard-deviation bands (self-consistent with the daily bar interval used
throughout this repo's other strategies), rather than reimplementing an
intraday session anchor we have no minute-bar data for.

Signal logic
------------
- Rolling VWAP over `vwap_window` days: sum(close*volume)/sum(volume).
- Rolling std of (close - vwap) over `vwap_window` days -> SD bands at
  `sd_mult` standard deviations above/below VWAP.
- Trend/chop regime filter: |SMA(trend_fast) - SMA(trend_slow)| / ATR(atr_window)
  -- below `regime_threshold` = "balanced" (chop, mean-reversion-friendly);
  at/above = "trending" (gate OFF, no new entries).
- Entry (long): close crosses below the lower band AND regime is balanced.
- Entry (short... not used, equity/crypto long-only per repo convention):
  N/A -- long-only design, matching other accepted strategies in this repo.
- Exit: close crosses back above VWAP (mean-reversion target reached), OR
  regime flips to trending (risk-off exit), OR max_hold_days elapsed.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _true_range(df: pd.DataFrame) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def generate_signals(
    price_df: pd.DataFrame,
    vwap_window: int = 20,
    sd_mult: float = 2.0,
    trend_fast: int = 10,
    trend_slow: int = 50,
    atr_window: int = 14,
    regime_threshold: float = 1.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)
    # avoid zero/NaN volume degenerating the vwap calc
    volume = volume.replace(0, float("nan")).ffill().fillna(1.0)

    pv = close * volume
    rolling_pv = pv.rolling(vwap_window).sum()
    rolling_vol = volume.rolling(vwap_window).sum()
    vwap = rolling_pv / rolling_vol

    dev = close - vwap
    dev_std = dev.rolling(vwap_window).std()
    lower_band = vwap - sd_mult * dev_std

    sma_fast = close.rolling(trend_fast).mean()
    sma_slow = close.rolling(trend_slow).mean()
    atr = _true_range(df).rolling(atr_window).mean()
    trend_strength = (sma_fast - sma_slow).abs() / atr.replace(0, float("nan"))
    balanced_regime = trend_strength <= regime_threshold

    entry = (close < lower_band) & balanced_regime.fillna(False)
    exit_meanrev = close >= vwap
    exit_regime_flip = ~balanced_regime.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    vwap_window: int = 20,
    sd_mult: float = 2.0,
    trend_fast: int = 10,
    trend_slow: int = 50,
    atr_window: int = 14,
    regime_threshold: float = 1.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the strategy's daily return series (position-weighted, no costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        vwap_window=vwap_window,
        sd_mult=sd_mult,
        trend_fast=trend_fast,
        trend_slow=trend_slow,
        atr_window=atr_window,
        regime_threshold=regime_threshold,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    # position at time i determines exposure to return realized over [i-1, i] -> shift 1
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
