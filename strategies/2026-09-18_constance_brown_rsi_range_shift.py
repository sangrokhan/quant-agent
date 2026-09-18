"""Strategy: Constance Brown RSI Range-Shift Regime (Bull/Bear Range Rules).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-120):
Per Constance Brown's well-documented "RSI Range Rules" (corroborated
across multiple independent sources read this iteration via browser_exec
fallback -- web_search's DDGS backend errored/was avoided in favor of
direct Google SERP browsing: MetaStock forum thread on Brown's Range
Rules, LuxAlgo's Constance Brown Studies indicator library page, and
fortraders.com's RSI overbought/oversold explainer, all independently
stating the same core numeric rule): unlike the textbook assumption that
RSI(14) oscillates in a fixed 30-70 (or 20-80) band regardless of trend,
Brown's empirical observation is that in a BULLISH regime RSI(14) tends to
range between roughly 40 and 80 (with 40 acting as *support* on pullbacks,
not an oversold buy signal), while in a BEARISH regime RSI(14) tends to
range between roughly 20 and 60 (with 60 acting as *resistance* on
bounces, not an overbought sell signal). This is architecturally distinct
from every RSI-threshold strategy already tested in this repo (all of
which use FIXED oversold/overbought levels regardless of the prevailing
trend) -- here the trend itself (defined by a slower SMA, per LuxAlgo's
own "RSI clearing 60 marks bull-range behavior, losing 40 the bear range"
regime-shift framing) determines which RSI band is "live," and price
pulling back to the LOWER edge of the CURRENT regime's RSI band is read as
a buyable dip-in-trend, not a reversal signal.

Signal logic
------------
For each bar t:
  - Compute RSI(rsi_period) (default 14, Wilder's smoothing).
  - Compute a slower trend filter: close vs SMA(trend_window) (default
    200) determines the prevailing regime -- bull_regime = close >
    SMA(trend_window).
  - In a bull regime: the "buy zone" is RSI dipping to/below
    bull_support_level (default 40, source's stated support level) while
    still above bull_floor_level (default 30, a safety floor -- if RSI
    falls all the way through 40 down toward 30 that's Brown's own signal
    the bull regime itself may be breaking down, not a dip to buy) --
    entry when RSI crosses back UP through bull_support_level from below
    (bounce off support confirmed), exit when RSI reaches
    bull_resistance_level (default 80, source's stated bull-range
    ceiling) or the regime itself flips to bearish (close crosses below
    SMA(trend_window)).
  - In a bear regime: per repo convention (SAFETY.md/long-only design),
    do NOT take any dip-buys -- stay flat. (Source's own bear-range
    rule 20-60 is the mirror-image short-side signal; testing it would
    require short-selling infrastructure this repo's strategies avoid.)
  - Long-only, single position.

Interface contract for validators (see validation/validators.py) and
grid_test (see validation/grid_test.py):
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} position series aligned to price_df.index.
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Daily strategy returns (position-weighted, no transaction costs
        applied here).

Tunable params (all keyword args, per RESEARCH_LOOP.md Step 5 contract):
    rsi_period (default 14)
    trend_window (default 200)
    bull_support_level (default 40)
    bull_floor_level (default 30)
    bull_resistance_level (default 80)
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


def _rsi_wilder(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.fillna(50.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    trend_window: int = 200,
    bull_support_level: float = 40.0,
    bull_floor_level: float = 30.0,
    bull_resistance_level: float = 80.0,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi_wilder(close, rsi_period)
    sma = close.rolling(trend_window).mean()
    bull_regime = close > sma

    position = pd.Series(0, index=close.index, dtype=int)
    pos = 0
    for i in range(len(close)):
        if np.isnan(sma.iloc[i]):
            position.iloc[i] = 0
            continue

        in_bull = bool(bull_regime.iloc[i])
        r = rsi.iloc[i]
        r_prev = rsi.iloc[i - 1] if i > 0 else r

        if pos == 1:
            # Exit on reaching the bull-range ceiling, or regime flipping bearish,
            # or RSI falling all the way through the floor (regime-break signal).
            if (not in_bull) or r >= bull_resistance_level or r < bull_floor_level:
                pos = 0
        else:
            if in_bull:
                # Entry: RSI bounced UP through the support level from below
                # (confirmed bounce off Brown's stated bull-range support),
                # and hasn't already broken down through the safety floor.
                crossed_up_support = (r_prev < bull_support_level) and (r >= bull_support_level)
                if crossed_up_support and r >= bull_floor_level:
                    pos = 1

        position.iloc[i] = pos

    return position.fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    trend_window: int = 200,
    bull_support_level: float = 40.0,
    bull_floor_level: float = 30.0,
    bull_resistance_level: float = 80.0,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        rsi_period=rsi_period,
        trend_window=trend_window,
        bull_support_level=bull_support_level,
        bull_floor_level=bull_floor_level,
        bull_resistance_level=bull_resistance_level,
    )
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
