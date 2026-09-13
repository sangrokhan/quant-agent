"""Strategy: Random Forest daily direction classifier, long-only, rolling
walk-forward retrained.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per https://blog.quantinsti.com/random-forest-algorithm-in-python/ (read via
browser_exec this iteration), a RandomForestClassifier trained on 4 simple
daily features -- (Open-Close)/Open, (High-Low)/Low, a 5-day rolling std of
returns (std_5), and a 5-day rolling mean of returns (ret_5) -- can predict
next-day price direction (up/down) well enough to generate a long-only
signal (go long when the model predicts UP, flat when it predicts DOWN).
The source's own single static 75/25 train/test split reports only 50.7%
test accuracy (essentially a coin flip) using a fixed one-time fit -- this
iteration tests whether a ROLLING walk-forward retrain (refit every
`retrain_period` trading days on a trailing `train_window`-day window,
predicting only strictly out-of-sample future days) produces a more
consistent, exploitable directional edge than the source's single static
fit, since a model retrained periodically should adapt better to regime
drift than one fit once on old data and never updated.

This is the first machine-learning classifier strategy tried in this repo
(no RandomForest/sklearn-classifier entries exist yet in
knowledge_base/strategies_index.jsonl) -- distinct from every rule-based
technical-indicator/calendar-anomaly strategy already tested.

Signal logic
------------
- Features (computed causally, no look-ahead): open_close_pct =
  (open-close)/open; high_low_pct = (high-low)/low; std_5 = rolling 5-day
  std of daily pct returns; ret_5 = rolling 5-day mean of daily pct
  returns.
- Target (for training only): 1 if next day's close > today's close, else 0.
- Every `retrain_period` trading days, fit a fresh RandomForestClassifier
  on the trailing `train_window` days of (features, target) pairs
  STRICTLY preceding the current day (no look-ahead: the target for day t
  uses close[t+1], so the last usable training row is day (current-2)).
- Predict on each subsequent day using the most recently fitted model
  (out-of-sample, walk-forward) until the next retrain point.
- Position: 1 (long) when predicted class == 1 (up), else 0 (flat) --
  long-only per SAFETY.md (no shorting).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    feat = pd.DataFrame(index=df.index)
    feat["open_close_pct"] = (df["open"] - df["close"]) / df["open"]
    feat["high_low_pct"] = (df["high"] - df["low"]) / df["low"]
    pct_change = df["close"].pct_change()
    feat["std_5"] = pct_change.rolling(5).std()
    feat["ret_5"] = pct_change.rolling(5).mean()
    return feat


def generate_signals(
    price_df: pd.DataFrame,
    train_window: int = 500,
    retrain_period: int = 63,
    n_estimators: int = 100,
    max_depth: int = 5,
    random_state: int = 42,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    from sklearn.ensemble import RandomForestClassifier

    df = _prep(price_df)
    close = df["close"]
    feat = _build_features(df)
    target = (close.shift(-1) > close).astype(int)

    valid = feat.notna().all(axis=1)
    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)

    model = None
    first_usable = train_window + 10  # warm-up before first possible fit
    for i in range(n):
        if i < first_usable:
            continue
        # Retrain at the start (i == first_usable) and every retrain_period bars.
        if model is None or (i - first_usable) % retrain_period == 0:
            train_start = max(0, i - train_window)
            # Last usable training index is i-2 (target needs close[t+1],
            # and we must not use info from day i itself / its own target).
            train_end = i - 2
            if train_end <= train_start:
                continue
            X_train = feat.iloc[train_start:train_end]
            y_train = target.iloc[train_start:train_end]
            mask = X_train.notna().all(axis=1) & y_train.notna()
            X_train, y_train = X_train[mask], y_train[mask]
            if len(X_train) < 50 or y_train.nunique() < 2:
                continue
            model = RandomForestClassifier(
                n_estimators=n_estimators, max_depth=max_depth,
                random_state=random_state, n_jobs=1,
            )
            model.fit(X_train.values, y_train.values)

        if model is None or not bool(valid.iloc[i]):
            position.iloc[i] = 0
            continue

        x_today = feat.iloc[[i]].values
        pred = model.predict(x_today)[0]
        position.iloc[i] = int(pred)

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
