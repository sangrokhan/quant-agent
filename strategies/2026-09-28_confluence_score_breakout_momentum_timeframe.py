"""Strategy: Multi-dimensional confluence-score entry filter (OHLCV-only
adaptation of Draconic's 5-dimension Confluence Scoring Method), long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-28-085):
Per Draconic's "The Confluence Scoring Method"
(https://draconic.ai/tradecraft/confluence-scoring-method, read via
browser_exec since web_extract's ddgs backend is search-only), the source's
own key insight is that stacking correlated indicators (e.g. RSI+MACD+
Stochastic, all momentum) is NOT true confluence -- it's counting one
opinion multiple times. Genuine confluence requires INDEPENDENT signal
categories (the source's own 5: price structure, momentum quality, flow
confirmation, options positioning, timeframe alignment), each scored 0/1,
summed into a conviction score.

This repo's data/loaders.py only exposes single-symbol daily OHLCV (no
options chain, no tick-level order flow/CVD) -- so 2 of the source's 5
dimensions (flow confirmation, options positioning) are feasibility-blocked
and dropped, keeping the 3 genuinely OHLCV-derivable, independent
dimensions:

1. Price structure: close breaks above its own rolling N-day high
   (structural breakout, not just a drawn trendline) AND same-day volume
   exceeds its rolling average by vol_mult (source's own "level with
   structural significance supported by >=2 independent signals" idea,
   adapted to breakout + volume confirmation instead of order-block/FVG
   confluence which requires intraday microstructure data we don't have).
2. Momentum quality: source's own "is momentum accelerating or exhausting"
   -- N-day rate-of-change is itself increasing versus the prior N-day
   window (velocity expanding), NOT just "RSI is above 50" (which the
   source explicitly calls out as re-measuring the same momentum
   dimension already captured elsewhere).
3. Timeframe alignment: source's own "does the higher timeframe agree" --
   price is above BOTH its daily trend SMA AND a 5x-longer weekly-scale
   SMA (proxy for one timeframe up, since this repo has no native weekly
   bars).

Distinct from this repo's prior multi-dimensional construction
(2026-09-27-093, an EXIT-side exhaustion score using velocity deceleration
+ swing-duration expansion + statistical extremes from ZigZag pivots) --
this is an ENTRY-side confluence filter using breakout-structure +
momentum-acceleration + multi-scale-trend-alignment, a different triple of
dimensions from a different Draconic article.

Signal logic
------------
- Long entry: confluence_score (0-3, sum of the three 0/1 dimensions above)
  >= min_score, gated by an overall SMA(trend_window) uptrend filter (avoid
  counter-trend entries the source's own framework doesn't address since
  it assumes a directional bias is already chosen).
- Exit: confluence_score drops to 0 (source's own "when one dimension
  actively contradicts, that changes the math" taken to its logical
  extreme for a single-position system), OR close falls back below
  SMA(trend_window) (trend invalidated), OR max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1}
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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
    breakout_window: int = 20,
    vol_mult: float = 1.2,
    mom_window: int = 10,
    trend_window: int = 50,
    weekly_scale: int = 5,
    min_score: int = 2,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    # Dimension 1: price structure (breakout + volume confirmation)
    rolling_high = close.rolling(breakout_window).max().shift(1)
    avg_vol = volume.rolling(breakout_window).mean()
    dim_structure = (close > rolling_high) & (volume > avg_vol * vol_mult)

    # Dimension 2: momentum quality (velocity expanding, not just direction)
    roc = close.pct_change(mom_window)
    roc_prior = roc.shift(mom_window)
    dim_momentum = roc > roc_prior

    # Dimension 3: timeframe alignment (daily SMA AND longer weekly-scale SMA)
    sma_daily = close.rolling(trend_window).mean()
    sma_weekly = close.rolling(trend_window * weekly_scale).mean()
    dim_timeframe = (close > sma_daily) & (close > sma_weekly)

    confluence_score = (
        dim_structure.astype(int) + dim_momentum.astype(int) + dim_timeframe.astype(int)
    )

    uptrend_gate = close > sma_daily
    entry = (confluence_score >= min_score) & uptrend_gate.fillna(False)
    exit_score = confluence_score == 0
    exit_trend = close < sma_daily

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if pd.isna(sma_weekly.iloc[i]):
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(exit_score.iloc[i]) or bool(exit_trend.iloc[i]) or held >= max_hold_days:
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
