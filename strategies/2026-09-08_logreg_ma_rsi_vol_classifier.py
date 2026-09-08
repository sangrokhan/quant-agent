"""Strategy: rolling walk-forward Logistic Regression classifier (MA-crossover
+ RSI + volume features) predicting next-day up/down direction.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-177):
Per QuantInsti "Machine Learning Logistic Regression: Python, Trading, and
More" (https://blog.quantinsti.com/machine-learning-logistic-regression-python/),
a worked example builds a binary logistic-regression classifier for next-day
stock price direction using three predictor variables: (1) a moving-average
crossover binary indicator (short MA above long MA), (2) the RSI value, and
(3) trading volume. The trader buys when the model's predicted probability
of an up day exceeds a threshold (source example: p > 0.7).

Implementation: a rolling walk-forward `sklearn.linear_model.LogisticRegression`
refit every `refit_every` days on a trailing `train_window` days of the
three features (MA-crossover binary, RSI(14), and volume z-scored against
its own trailing history) with next-day up/down as the label, strictly
no-lookahead (fit uses only data through day t-1, predicts day t). Long
only when the model's predicted probability of an up day exceeds
`prob_threshold`.

First supervised-machine-learning (logistic regression classifier) entry in
this repo -- mechanically distinct from every prior rule-based indicator
threshold/crossover strategy since the entry rule itself (the linear
decision boundary in feature space) is fit via maximum-likelihood
estimation on trailing data rather than hand-specified, and also distinct
from the unsupervised HMM regime filter (2026-09-08-173, which clusters
return-distribution states without a next-day-direction label).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    ma_short: int = 50,
    ma_long: int = 200,
    rsi_window: int = 14,
    vol_zscore_window: int = 60,
    train_window: int = 504,
    refit_every: int = 21,
    prob_threshold: float = 0.55,
    min_train: int = 252,
) -> pd.Series:
    """Return a {0,1} long/flat position series from a rolling logistic
    regression classifier's predicted up-probability."""
    from sklearn.linear_model import LogisticRegression

    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(0.0, index=close.index)

    sma_short = close.rolling(ma_short).mean()
    sma_long = close.rolling(ma_long).mean()
    ma_crossover = (sma_short > sma_long).astype(float)

    rsi = _rsi(close, rsi_window)

    vol_mean = volume.rolling(vol_zscore_window).mean()
    vol_std = volume.rolling(vol_zscore_window).std()
    vol_z = ((volume - vol_mean) / vol_std.replace(0, np.nan)).fillna(0.0)

    features = pd.DataFrame({
        "ma_crossover": ma_crossover,
        "rsi": rsi,
        "vol_z": vol_z,
    })

    next_day_up = (close.shift(-1) > close).astype(float)  # label for day t (uses t+1 price)

    position = pd.Series(0, index=close.index, dtype=int)
    n = len(close)
    if n < min_train + 2:
        return position

    model = None
    for t in range(min_train, n):
        if (t - min_train) % refit_every == 0:
            train_start = max(0, t - train_window)
            # Labels for training rows must only use info available strictly
            # before day t: the label for row j is whether day j+1 > day j,
            # so the LAST usable training row is t-2 (label needs day t-1,
            # both known before we predict day t).
            train_end = max(train_start, t - 1)
            X_train = features.iloc[train_start:train_end].values
            y_train = next_day_up.iloc[train_start:train_end].values
            mask = ~pd.isna(X_train).any(axis=1) & ~pd.isna(y_train)
            X_train, y_train = X_train[mask], y_train[mask]
            if len(X_train) < min_train // 2 or len(set(y_train.tolist())) < 2:
                position.iloc[t] = position.iloc[t - 1] if t > 0 else 0
                continue
            try:
                model = LogisticRegression(max_iter=200)
                model.fit(X_train, y_train)
            except Exception:
                model = None

        if model is None:
            position.iloc[t] = 0
            continue

        x_today = features.iloc[t:t + 1].values
        if pd.isna(x_today).any():
            position.iloc[t] = 0
            continue
        try:
            prob_up = model.predict_proba(x_today)[0, list(model.classes_).index(1.0)] \
                if 1.0 in model.classes_ else 0.0
        except Exception:
            prob_up = 0.0
        position.iloc[t] = int(prob_up > prob_threshold)

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
