"""Strategy: Walk-forward Gradient Boosting classifier on
RSI/ROC/volatility/volume features, predicting forward-1-bar return sign.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per the "Machine Learning for Algorithm Trading" gradient-boosting chapter
(https://ml4trading.io/third-edition/chapters/12_gradient_boosting/ and
https://github.com/stefan-jansen/machine-learning-for-trading/tree/main/12_gradient_boosting,
read this iteration via web_extract -- web_search worked for this query),
the standard approach for tabular financial features is a gradient-boosted
tree ensemble (here: sklearn's GradientBoostingClassifier, since xgboost is
not installed in this repo's venv) trained walk-forward on daily technical
features to forecast the sign of the next bar's return, then act on the
prediction directly as a long/flat signal. This is the FIRST tree-ensemble
(gradient boosting) ML strategy in this repo -- prior ML entries are a kNN
classifier (2026-09-27-114/115, accepted QQQ) and two unsupervised
Gaussian-HMM regime filters (2026-09-08-173, 2026-09-09-014, both
rejected). Gradient boosting differs fundamentally in both algorithm
(sequential residual-fitting trees vs. instance-based distance voting)
and feature set (4 features here: RSI, rate-of-change, realized-vol
percentile, volume z-score, vs. the KNN strategy's 2 features layered on
a separate SuperTrend baseline) -- this strategy trades directly off the
classifier's own prediction confidence, with no separate trend baseline.

Signal logic
------------
- Features per bar: RSI(rsi_period), ROC(roc_period) (rate of change,
  pct_change over roc_period bars), rolling realized-volatility
  percentile-rank(vol_window) over a trailing 252-day lookback, and a
  rolling z-score of volume over vol_window bars.
- Walk-forward GradientBoostingClassifier training: every retrain_every
  bars, fit sklearn.ensemble.GradientBoostingClassifier(n_estimators=
  n_estimators, max_depth=max_depth, learning_rate=0.05) on all PRIOR bars
  (strictly before the current retrain point, minimum train_min_bars)
  using the 4 features as X and sign(next-bar return) as y (+1/-1, ties
  toward -1). Predict P(y=+1) for bars until the next retrain point.
- Long condition: P(y=+1) >= 0.5 + confidence_buffer. Long-only (no
  shorting, per SAFETY.md); flat whenever the classifier hasn't been
  trained yet or the condition fails.
- Exit is implicit: position flips flat as soon as the classifier's
  prediction confidence drops below threshold on any subsequent bar
  (no separate max-hold/time-stop needed since predictions update daily).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


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


def _vol_zscore(volume: pd.Series, window: int) -> pd.Series:
    mean = volume.rolling(window, min_periods=window).mean()
    std = volume.rolling(window, min_periods=window).std()
    z = (volume - mean) / std.replace(0.0, np.nan)
    return z.fillna(0.0)


def _gbm_bullish_proba(
    features: pd.DataFrame,
    close: pd.Series,
    n_estimators: int,
    max_depth: int,
    retrain_every: int,
    train_min_bars: int,
) -> pd.Series:
    """Walk-forward GradientBoostingClassifier: predict P(next-bar return>0)
    at each bar using only strictly-prior data, refit every retrain_every bars."""
    from sklearn.ensemble import GradientBoostingClassifier

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
            if len(X_train) >= max(50, train_min_bars // 4) and len(np.unique(y_train)) > 1:
                model = GradientBoostingClassifier(
                    n_estimators=n_estimators, max_depth=max_depth, learning_rate=0.05,
                    random_state=42,
                )
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
    rsi_period: int = 14,
    roc_period: int = 10,
    vol_window: int = 20,
    n_estimators: int = 100,
    max_depth: int = 3,
    retrain_every: int = 63,
    train_min_bars: int = 252,
    confidence_buffer: float = 0.05,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    rsi = _rsi(close, rsi_period)
    roc = close.pct_change(roc_period) * 100.0
    vol_pct = _vol_percentile(close, vol_window)
    vol_z = _vol_zscore(volume, vol_window)
    features = pd.DataFrame({"rsi": rsi, "roc": roc, "vol_pct": vol_pct, "vol_z": vol_z})

    proba_up = _gbm_bullish_proba(features, close, n_estimators, max_depth, retrain_every, train_min_bars)
    position = (proba_up >= (0.5 + confidence_buffer)).fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
