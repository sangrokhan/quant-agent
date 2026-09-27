"""Strategy: SuperTrend baseline confirmed by a k-nearest-neighbors (kNN)
RSI+volatility classifier -- only take the SuperTrend direction when the
kNN vote agrees.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per LuxAlgo's "KNN Supertrend Horizon" indicator
(https://www.luxalgo.com/library/indicator/knn-supertrend-horizon/, published
23 Mar 2026, read via browser_exec this iteration -- web_search DDGS backend
returned no results for this specific query), the source's own disclosed
mechanism:

1. A standard ATR-based SuperTrend baseline gives a directional flip signal
   (up/down), same construction as this repo's existing
   2026-09-03_supertrend_atr_longonly.py.
2. A k-nearest-neighbors classifier encodes each bar's RSI and ATR-based
   realized-volatility percentile as a 2-feature vector, searches the most
   similar historical bars within a trailing `search_window`, and takes a
   majority vote among those neighbors' FORWARD 1-bar direction (label =
   sign of next-bar return) to classify current conditions as
   bullish/bearish.
3. Source's own trading rule ("How to Trade" section): "Only when that vote
   agrees with the Supertrend direction does the colored horizon print,
   trimming the weak flips a raw trend line suffers in chop." I.e. the
   composite signal is long only when BOTH (a) SuperTrend direction is up
   AND (b) the kNN classifier's bullish-vote fraction clears a confidence
   buffer above 50% ("ML Confidence Buffer" setting -- "holds flips back
   until the classification moves decisively past the midpoint").

This iteration operationalizes that exact dual-confirmation rule as
generate_signals/generate_returns: SuperTrend direction (reusing this
repo's existing recursive SuperTrend construction) AND a from-scratch
sklearn KNeighborsClassifier trained walk-forward (expanding window, no
look-ahead -- refit periodically on data strictly before the current bar)
on [RSI(14), rolling ATR-percentile] features with a forward-1-bar-return
sign label, requiring the classifier's positive-class probability to clear
0.5 + confidence_buffer before confirming a long SuperTrend flip.

This is a genuinely novel angle for this repo: prior HMM-based regime
filters (2026-09-08-173, 2026-09-09-014, both rejected) used unsupervised
Gaussian-mixture state discovery on return distributions, NOT a supervised
kNN classifier voting on RSI/volatility features against forward-return
labels layered on top of an existing SuperTrend baseline. KB search for
"KNN"/"k-nearest"/"nearest neighbor" in strategies_index.jsonl returned
zero true matches (one spurious substring hit in an unrelated no_candidate
summary), confirming this is the first true KNN-classifier strategy tested.

Signal logic
------------
- SuperTrend direction (ATR period=atr_period, multiplier=st_multiplier),
  same recursive band construction as 2026-09-03_supertrend_atr_longonly.py.
- Features per bar: RSI(rsi_period) and a rolling realized-volatility
  percentile-rank(vol_window) of daily returns over a trailing 252-day
  window (both bounded roughly [0,100], comparable scale, no need for
  extra normalization).
- Walk-forward kNN training: every retrain_every bars, fit
  sklearn.neighbors.KNeighborsClassifier(n_neighbors=k_neighbors) on all
  PRIOR bars (index < current retrain point, minimum train_min_bars) using
  [RSI, vol_percentile] as X and sign(next-bar return) as y (+1/-1, ties
  treated as -1 to keep binary). Predict P(y=+1) for bars until the next
  retrain point using predict_proba.
- Composite long condition: SuperTrend direction == up AND
  P(y=+1) >= 0.5 + confidence_buffer.
- Long-only (no shorting, per SAFETY.md); flat whenever either condition
  fails or the classifier hasn't been trained yet (insufficient history).

Source read this iteration:
- https://www.luxalgo.com/library/indicator/knn-supertrend-horizon/
  (LuxAlgo, published 23 Mar 2026 -- full mechanical description: kNN
  RSI+volatility classifier gating a SuperTrend baseline, confidence-buffer
  concept, disclosed via browser_exec after web_search returned no results).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept the strategy's tunable parameters as kwargs.
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


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def _supertrend_direction(
    high: pd.Series, low: pd.Series, close: pd.Series, atr_period: int, multiplier: float
) -> pd.Series:
    atr = _atr(high, low, close, atr_period)
    hl2 = (high + low) / 2.0
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    n = len(close)
    final_upper = pd.Series(np.nan, index=close.index)
    final_lower = pd.Series(np.nan, index=close.index)
    direction = pd.Series(1, index=close.index, dtype=int)

    for i in range(n):
        if i == 0 or np.isnan(atr.iloc[i]):
            final_upper.iloc[i] = basic_upper.iloc[i]
            final_lower.iloc[i] = basic_lower.iloc[i]
            direction.iloc[i] = 1
            continue

        prev_final_upper = final_upper.iloc[i - 1]
        prev_final_lower = final_lower.iloc[i - 1]
        prev_close = close.iloc[i - 1]

        cur_upper = basic_upper.iloc[i]
        if not np.isnan(prev_final_upper) and (cur_upper > prev_final_upper) and (prev_close <= prev_final_upper):
            cur_upper = prev_final_upper
        final_upper.iloc[i] = cur_upper

        cur_lower = basic_lower.iloc[i]
        if not np.isnan(prev_final_lower) and (cur_lower < prev_final_lower) and (prev_close >= prev_final_lower):
            cur_lower = prev_final_lower
        final_lower.iloc[i] = cur_lower

        prev_direction = direction.iloc[i - 1]
        if prev_direction == 1:
            direction.iloc[i] = -1 if close.iloc[i] < final_lower.iloc[i] else 1
        else:
            direction.iloc[i] = 1 if close.iloc[i] > final_upper.iloc[i] else -1

    return direction


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def _vol_percentile(close: pd.Series, vol_window: int, lookback: int = 252) -> pd.Series:
    ret = close.pct_change()
    realized_vol = ret.rolling(vol_window, min_periods=vol_window).std()
    pct = realized_vol.rolling(lookback, min_periods=vol_window).rank(pct=True) * 100.0
    return pct.fillna(50.0)


def _knn_bullish_proba(
    features: pd.DataFrame,
    close: pd.Series,
    k_neighbors: int,
    retrain_every: int,
    train_min_bars: int,
) -> pd.Series:
    """Walk-forward kNN classifier: predict P(next-bar return > 0) at each
    bar using only strictly-prior data, refit every `retrain_every` bars."""
    from sklearn.neighbors import KNeighborsClassifier

    n = len(features)
    proba = pd.Series(np.nan, index=features.index)
    fwd_ret = close.pct_change().shift(-1)
    labels = (fwd_ret > 0).astype(int)

    X = features.values
    y = labels.values

    model = None
    next_retrain = train_min_bars

    for i in range(n):
        if i >= train_min_bars and (model is None or i >= next_retrain):
            train_end = i  # strictly prior bars only (no look-ahead)
            X_train = X[:train_end]
            y_train = y[:train_end]
            valid = ~np.isnan(X_train).any(axis=1) & ~np.isnan(y_train)
            X_train = X_train[valid]
            y_train = y_train[valid]
            if len(X_train) >= max(k_neighbors, 10) and len(np.unique(y_train)) > 1:
                model = KNeighborsClassifier(n_neighbors=k_neighbors)
                model.fit(X_train, y_train)
            next_retrain = i + retrain_every

        if model is not None and not np.isnan(X[i]).any():
            classes = list(model.classes_)
            if 1 in classes:
                p = model.predict_proba(X[i : i + 1])[0][classes.index(1)]
            else:
                p = 0.0
            proba.iloc[i] = p

    return proba


def generate_signals(
    price_df: pd.DataFrame,
    atr_period: int = 10,
    st_multiplier: float = 3.0,
    rsi_period: int = 14,
    vol_window: int = 20,
    k_neighbors: int = 15,
    retrain_every: int = 63,
    train_min_bars: int = 252,
    confidence_buffer: float = 0.1,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    direction = _supertrend_direction(high, low, close, atr_period, st_multiplier)
    st_up = direction == 1

    rsi = _rsi(close, rsi_period)
    vol_pct = _vol_percentile(close, vol_window)
    features = pd.DataFrame({"rsi": rsi, "vol_pct": vol_pct})

    proba_up = _knn_bullish_proba(features, close, k_neighbors, retrain_every, train_min_bars)
    ml_confirms = proba_up >= (0.5 + confidence_buffer)

    position = (st_up.fillna(False) & ml_confirms.fillna(False)).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    atr_period: int = 10,
    st_multiplier: float = 3.0,
    rsi_period: int = 14,
    vol_window: int = 20,
    k_neighbors: int = 15,
    retrain_every: int = 63,
    train_min_bars: int = 252,
    confidence_buffer: float = 0.1,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        atr_period=atr_period,
        st_multiplier=st_multiplier,
        rsi_period=rsi_period,
        vol_window=vol_window,
        k_neighbors=k_neighbors,
        retrain_every=retrain_every,
        train_min_bars=train_min_bars,
        confidence_buffer=confidence_buffer,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
