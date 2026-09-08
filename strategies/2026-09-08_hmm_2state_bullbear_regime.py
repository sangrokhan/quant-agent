"""Strategy: 2-state Gaussian Hidden Markov Model (HMM) bull/bear regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-173):
Per QuantifiedStrategies.com "Hidden Markov Model Market Regimes: How HMM
Detects Market Regimes in Trading Strategies"
(https://www.quantifiedstrategies.com/hidden-markov-model-market-regimes/),
a 2-state Gaussian HMM fit on an asset's daily log returns typically
discovers one "low-volatility bull" hidden state (relatively small positive
mean return, low variance) and one "high-volatility bear/crisis" hidden
state (negative mean return, high variance). The source notes that using an
HMM to avoid trades during the detected high-volatility/bear regime has been
shown to eliminate many losing trades and improve Sharpe ratio versus a
static always-invested strategy.

Implementation: fit a `hmmlearn.hmm.GaussianHMM` with `n_components=2` on a
rolling trailing window of the asset's own daily log returns (refit every
`refit_every` days, walk-forward/no-lookahead: only data up to and including
day t-1 is used to decode day t's state), label the state with the HIGHER
mean return as "bull", and go long only when the model's Viterbi-decoded
most-likely current state is "bull"; flat otherwise (captures the "bear"
regime as well as ambiguous/undetermined periods before the first refit).

First Hidden Markov Model / statistical regime-detection entry in this
repo -- mechanically distinct from all prior rule-based regime gates
(realized-vol percentile, ATR percentile, correlation-ratio, credit-spread,
etc.) since the regime boundary here is learned via unsupervised
expectation-maximization (Baum-Welch) on the return distribution itself,
not a hand-specified threshold on an observable indicator.

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


def generate_signals(
    price_df: pd.DataFrame,
    train_window: int = 504,
    refit_every: int = 21,
    min_train: int = 252,
) -> pd.Series:
    """Return a {0,1} long/flat position series based on a rolling-refit
    2-state Gaussian HMM bull/bear regime decode.

    No-lookahead: at each refit point t, the HMM is fit ONLY on log returns
    from [t - train_window, t) (i.e. strictly before day t), then used to
    decode the state for day t and hold that decode until the next refit.
    """
    from hmmlearn.hmm import GaussianHMM

    df = _prep(price_df)
    close = df["close"]
    log_ret = np.log(close / close.shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    n = len(close)
    if n < min_train + 2:
        return position

    current_bull = False
    for t in range(min_train, n):
        if (t - min_train) % refit_every == 0:
            train_start = max(0, t - train_window)
            train_data = log_ret.iloc[train_start:t].dropna().values.reshape(-1, 1)
            if len(train_data) < min_train // 2:
                position.iloc[t] = int(current_bull)
                continue
            try:
                model = GaussianHMM(n_components=2, covariance_type="diag",
                                     n_iter=50, random_state=42)
                model.fit(train_data)
                # Label the state with the higher mean return as "bull".
                means = model.means_.flatten()
                bull_state = int(np.argmax(means))
                # Decode the most recent observation's most-likely state
                # using only data strictly before day t (no lookahead).
                hidden_states = model.predict(train_data)
                latest_state = hidden_states[-1]
                current_bull = bool(latest_state == bull_state)
            except Exception:
                # Numerical fit failure (e.g. degenerate covariance) -- stay
                # flat/hold prior state rather than crashing the grid test.
                pass
        position.iloc[t] = int(current_bull)

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
