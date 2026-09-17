"""Strategy: Modified True Range "Goal Achievement %" as a continuous sizing
dial (Chris Lindgren, "Kiss & Touch With The Modified True Range", TASC
February 2015; EasyLanguage code republished in TASC's April 2015 Traders'
Tips), read this iteration via browser_exec at
https://traders.com/Documentation/FEEDbk_docs/2015/04/TradersTips.html
(exact EasyLanguage formula disclosed directly in the Traders' Tips code
section, after web_search DDGS backend errored on prior queries this run --
direct traders.com archive URL navigation to a previously-unvisited month,
discovered by walking forward from adjacent known TASC months already in
this repo's visited_urls.jsonl ledger).

Hypothesis (see knowledge_base/strategies_log.jsonl entry for this id):
Lindgren's Modified True Range (MTR = max(|High-PrevClose|, |Low-PrevClose|),
a one-sided variant of Wilder's True Range using only the larger of the two
gap-adjusted extremes rather than the full high-low-vs-prevclose max/min)
measures how often price moves a "Goal" amount in a single bar over a
rolling window (`GoalPctAchieved` = 100 * count(MTR>=Goal) / window, a
naturally bounded [0,100] rolling-frequency statistic, distinct from every
prior bounded trend-strength/volatility construction in this repo -- Stiffness
Indicator counts CLOSE-vs-MA-floor threshold crossings, Choppiness/VHF/Hurst
are continuous statistical/geometric measures, none count MTR->goal
threshold-achievement frequency). This iteration reframes GoalPctAchieved
(already bounded, used directly per this repo's Stiffness-Indicator
precedent) as a CONTINUOUS SIZING dial: high recent volatility-achievement
frequency scales exposure UP (a "volatility begets opportunity/momentum"
framing consistent with this repo's other continuous-sizing constructions),
gated by an SMA(trend_window) uptrend filter with a deadband to control
turnover. First Modified True Range strategy in this repo.

Exact formula (from TASC Feb 2015 / republished Apr 2015 TradeStation
EasyLanguage, as read this iteration):
    MTR = max(|High - Close[1]|, |Low - Close[1]|)
    GoalAchieved[t] = 1 if MTR[t] >= Goal else 0
    GoalPctAchieved = 100 * CountIf(GoalAchieved==1, PeriodLength) / PeriodLength

`Goal` in the source article is a fixed price-unit threshold (option-strike
oriented); here it's made scale-free by expressing it as
`goal_atr_mult` x ATR(atr_window) (re-derived each bar) so the strategy
transfers across symbols/price levels without a hardcoded dollar amount.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series (thresholded from the continuous
        sizing dial at 0.5 exposure for signal-series compatibility; the
        raw continuous exposure is what generate_returns actually uses).
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat(
        [h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def _exposure_dial(
    price_df: pd.DataFrame,
    period_length: int,
    goal_atr_mult: float,
    atr_window: int,
    trend_window: int,
    deadband: float,
    base_exposure: float,
    sensitivity: float,
) -> pd.Series:
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)

    mtr = pd.concat(
        [(high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = _atr(df, atr_window)
    goal = goal_atr_mult * atr

    goal_achieved = (mtr >= goal).astype(float)
    goal_pct_achieved = 100.0 * goal_achieved.rolling(period_length).sum() / period_length

    # Rescale bounded [0,100] to [-1, 1]
    centered = (goal_pct_achieved - 50.0) / 50.0

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    raw_exposure = base_exposure + sensitivity * centered
    raw_exposure = raw_exposure.clip(lower=0.0, upper=2.0)

    # deadband: only adjust exposure meaningfully away from base when the
    # dial's magnitude exceeds the deadband, else hold at base_exposure
    exposure = np.where(centered.abs() >= deadband, raw_exposure, base_exposure)
    exposure = pd.Series(exposure, index=df.index)
    exposure = np.where(uptrend, exposure, 0.0)
    exposure = pd.Series(exposure, index=df.index)
    exposure[goal_pct_achieved.isna() | sma_trend.isna()] = 0.0
    return exposure


def generate_signals(
    price_df: pd.DataFrame,
    period_length: int = 40,
    goal_atr_mult: float = 1.0,
    atr_window: int = 40,
    trend_window: int = 50,
    deadband: float = 0.15,
    base_exposure: float = 1.0,
    sensitivity: float = 0.5,
) -> pd.Series:
    """Return a {0,1} thresholded position series (exposure>=0.5 -> long)."""
    exposure = _exposure_dial(
        price_df, period_length, goal_atr_mult, atr_window, trend_window,
        deadband, base_exposure, sensitivity,
    )
    return (exposure >= 0.5).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    period_length: int = 40,
    goal_atr_mult: float = 1.0,
    atr_window: int = 40,
    trend_window: int = 50,
    deadband: float = 0.15,
    base_exposure: float = 1.0,
    sensitivity: float = 0.5,
) -> pd.Series:
    """Continuous-exposure daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = _exposure_dial(
        price_df, period_length, goal_atr_mult, atr_window, trend_window,
        deadband, base_exposure, sensitivity,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = exposure.shift(1).fillna(0) * daily_ret
    return strategy_ret
