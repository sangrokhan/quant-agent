"""Strategy: Adaptive RSI thresholds gated by TSI (True Strength Index) trend regime.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
An adaptive momentum-mean-reversion hybrid: TSI (double-smoothed
momentum-of-momentum oscillator, Ehlers/Blau family) determines whether the
market is in a trending or range-bound regime. RSI(14) oversold-cross
entries are widened (deeper oversold required, i.e. lower threshold) when
TSI confirms trend strength is weak/range-bound, but ONLY entries when TSI
is non-negative (avoid buying dips in a confirmed downtrend) -- long-only,
adapted from a Google AI-overview synthesis of TradingView/IG/Quantified
Strategies RSI+TSI adaptive-threshold hybrid articles (see source URL in
knowledge_base notes). Distinct from prior RSI-only or TSI-only entries in
this repo: this is the first strategy to *combine* TSI as a trend-strength
regime gate directly modulating the RSI entry threshold, rather than either
indicator alone or a static combination.

Signal logic
------------
- TSI = 100 * EMA(EMA(diff(close), r), s) / EMA(EMA(|diff(close)|, r), s)
  with r=25, s=13 (Blau's standard TSI parameters).
- TSI regime: "trending" when |TSI| > tsi_trend_threshold, else "range-bound".
- RSI(14) computed with Wilder smoothing.
- Adaptive oversold threshold: rsi_oversold_range (e.g. 35) when
  range-bound, rsi_oversold_trend (e.g. 25, deeper) when trending -- in a
  strong uptrend we require a deeper RSI dip before trusting a pullback
  entry, since shallow RSI dips are noise in a strong trend.
- Long entry: TSI >= 0 (uptrend or neutral, never fight a downtrend) AND
  RSI crosses back above its (regime-adaptive) oversold threshold from
  below.
- Exit: RSI crosses above rsi_exit_level (e.g. 60), OR TSI crosses below 0
  (trend flips bearish -- risk-off exit), OR after max_hold_days.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _tsi(close: pd.Series, r: int = 25, s: int = 13) -> pd.Series:
    diff = close.diff()
    ema1 = diff.ewm(span=r, adjust=False).mean()
    ema2 = ema1.ewm(span=s, adjust=False).mean()
    abs_ema1 = diff.abs().ewm(span=r, adjust=False).mean()
    abs_ema2 = abs_ema1.ewm(span=s, adjust=False).mean()
    tsi = 100 * (ema2 / abs_ema2.replace(0.0, 1e-12))
    return tsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    tsi_r: int = 25,
    tsi_s: int = 13,
    tsi_trend_threshold: float = 10.0,
    rsi_oversold_range: float = 35.0,
    rsi_oversold_trend: float = 25.0,
    rsi_exit_level: float = 60.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, window=rsi_window)
    tsi = _tsi(close, r=tsi_r, s=tsi_s)

    trending = tsi.abs() > tsi_trend_threshold
    oversold_threshold = pd.Series(
        [rsi_oversold_trend if t else rsi_oversold_range for t in trending.fillna(False)],
        index=close.index,
    )

    rsi_prev = rsi.shift(1)
    threshold_prev = oversold_threshold.shift(1)
    cross_up = (rsi_prev <= threshold_prev) & (rsi > oversold_threshold)
    entry = cross_up.fillna(False) & (tsi >= 0).fillna(False)

    exit_rsi = rsi > rsi_exit_level
    exit_tsi_flip = tsi < 0

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_rsi.iloc[i]) or bool(exit_tsi_flip.iloc[i]) or held >= max_hold_days:
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
