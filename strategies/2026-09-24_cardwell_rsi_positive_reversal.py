"""Strategy: Cardwell RSI "Positive Reversal" trend-continuation entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this entry),
sourced from three corroborating pages read via browser_exec this
iteration (web_search's DDGS backend returned empty/garbage results this
run, per RESEARCH_LOOP.md Step 2 fallback):

    - Google SERP snippet of tradethatswing.com ("Positive and Negative
      Reversals were developed by Andrew Cardwell ... Positive Reversal =
      Buy = RSI Lower Low, Price Higher Low.")
    - LuxAlgo glossary snippet ("A positive reversal occurs when RSI makes
      a lower low while price makes a higher low: momentum looks weaker,
      yet price holds firmer, and Cardwell reads that as ...")
    - gtlackey.com "Positive and Negative Reversal Patterns" (full page
      read directly): "a positive reversal shows up in a pullback during
      an uptrend where the chart has a lower RSI with a higher price when
      the pullback reverses ... give good entry points long for positive
      reversals."

This is the explicit MIRROR IMAGE of classic bullish divergence (which
this repo already tested extensively, e.g. 2026-09-03-019
rsi_bullish_divergence.py: price LOWER low + RSI HIGHER low, read as a
reversal-of-downtrend signal). Cardwell's positive reversal instead fires
DURING AN ESTABLISHED UPTREND on a pullback: price makes a HIGHER low
while RSI makes a LOWER low -- i.e. the pullback's momentum reading looks
weaker than the prior pullback even though price itself held up better,
which Cardwell reads as underlying demand strength (bearish-looking RSI
print that price refuses to confirm) and a continuation-buy signal, NOT a
reversal-of-trend signal. No prior "Cardwell"/"positive reversal" entries
in this repo's knowledge base (0 index hits) -- structurally distinct from
every regular/hidden RSI-divergence entry already tested (2026-09-03-019,
2026-09-09-003 hidden bullish divergence, 2026-09-11-020 general busted
pattern, etc.) because of the trend-context + inverted price/RSI polarity.

Signal logic
------------
- Uptrend gate: close > SMA(trend_window) (established uptrend context,
  per gtlackey's "pullback during an uptrend" framing -- Cardwell reversals
  are explicitly NOT a bottom-picking tool).
- Swing-low detection: identical N-bar centered local-minimum detector to
  this repo's existing divergence strategies (swing_window).
- Positive reversal confirmed at swing low i2 (most recent) vs the nearest
  prior swing low i1 within lookback_bars: close2 > close1 (price higher
  low) AND rsi2 < rsi1 (RSI lower low), with the uptrend gate active at i2.
  Entry the bar after confirmation.
- Exit: RSI crosses back above exit_rsi_level (momentum normalized /
  target likely reached, per gtlackey's own target-taking discussion),
  OR the uptrend gate breaks (close <= SMA(trend_window), Cardwell
  reversals lose their thesis once the underlying uptrend fails), OR after
  max_hold_days bars, whichever comes first.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
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
    trend_window: int = 50,
    exit_rsi_level: float = 60.0,
    max_hold_days: int = 15,
    lookback_bars: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Detects Cardwell "positive reversal" pattern between successive swing
    lows within a rolling `lookback_bars` window, only while close is above
    its `trend_window`-day SMA (uptrend gate): second (more recent) swing
    low has HIGHER price but LOWER RSI than the prior swing low. Enters
    long the bar after confirmation. Exits when RSI crosses back above
    exit_rsi_level, the trend gate breaks, or after max_hold_days bars,
    whichever comes first.
    """
    df = _prep(price_df)
    close = df["close"]
    rsi = _rsi(close, rsi_window)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend
    is_low = _swing_lows(close, swing_window)

    swing_idx = np.where(is_low.fillna(False).values)[0]
    n = len(close)
    entries = np.zeros(n, dtype=bool)

    for j in range(1, len(swing_idx)):
        i2 = swing_idx[j]
        prior_candidates = [i1 for i1 in swing_idx[:j] if i2 - i1 <= lookback_bars]
        if not prior_candidates:
            continue
        i1 = prior_candidates[-1]
        rsi1, rsi2 = rsi.iloc[i1], rsi.iloc[i2]
        px1, px2 = close.iloc[i1], close.iloc[i2]
        if pd.isna(rsi1) or pd.isna(rsi2):
            continue
        if bool(uptrend.iloc[i2]) and px2 > px1 and rsi2 < rsi1:
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
            trend_broke = not bool(uptrend.iloc[t]) if not pd.isna(sma_trend.iloc[t]) else False
            if (not pd.isna(rsi_t) and rsi_t > exit_rsi_level) or held >= max_hold_days or trend_broke:
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
