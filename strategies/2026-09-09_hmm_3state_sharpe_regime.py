"""Strategy: 3-state Gaussian Hidden Markov Model, invest only in the
best RISK-ADJUSTED (mean/std, not just highest-mean) hidden state.

Hypothesis (direct refinement of near-miss/rejection 2026-09-08-173, see
knowledge_base/strategies_log.jsonl):
The prior 2-state HMM regime filter (source:
https://www.quantifiedstrategies.com/hidden-markov-model-market-regimes/)
picked the state with the HIGHEST MEAN return as "bull" and stayed invested
whenever decoded into that state. Its own diagnosed failure mode was: QQQ
MDD 0.386 (decisive fail) despite passing Sharpe 1.061 -- i.e. with only 2
states, the "bull" state absorbed both genuinely calm low-vol uptrends AND
higher-volatility melt-up/euphoria periods (still positive-mean but high
variance), which QQQ experiences more than SPY. That inflated its
drawdown. This iteration's fix: fit a 3-state Gaussian HMM (adds a distinct
mid/transition state) on trailing log returns, and instead of picking the
state by mean return alone, pick the state that maximizes an in-sample
Sharpe-like score (mean/std) over the training window -- explicitly
favoring the calm high-quality regime over a high-mean-but-high-vol
euphoria regime. Same rolling walk-forward refit (no lookahead) as the
prior HMM strategy for a controlled, minimal-variable comparison.

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
    n_states: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series based on a rolling-refit
    N-state Gaussian HMM, invested only when decoded into the state with
    the best in-sample risk-adjusted (mean/std) score.

    No-lookahead: at each refit point t, the HMM is fit ONLY on log returns
    from [t - train_window, t) (strictly before day t), then used to decode
    the state for day t and hold that decode until the next refit.
    """
    from hmmlearn.hmm import GaussianHMM

    df = _prep(price_df)
    close = df["close"]
    log_ret = np.log(close / close.shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    n = len(close)
    if n < min_train + 2:
        return position

    current_invested = False
    for t in range(min_train, n):
        if (t - min_train) % refit_every == 0:
            train_start = max(0, t - train_window)
            train_data = log_ret.iloc[train_start:t].dropna().values.reshape(-1, 1)
            if len(train_data) < min_train // 2:
                position.iloc[t] = int(current_invested)
                continue
            try:
                model = GaussianHMM(n_components=n_states, covariance_type="diag",
                                     n_iter=50, random_state=42)
                model.fit(train_data)
                means = model.means_.flatten()
                stds = np.sqrt(model.covars_.flatten())
                # Risk-adjusted score per state (in-sample mean/std, i.e. a
                # crude per-state Sharpe proxy) -- pick the "best" state by
                # this score, not just highest mean.
                scores = means / np.where(stds > 1e-12, stds, 1e-12)
                best_state = int(np.argmax(scores))
                hidden_states = model.predict(train_data)
                latest_state = hidden_states[-1]
                current_invested = bool(latest_state == best_state)
            except Exception:
                # Numerical fit failure -- hold prior state rather than
                # crashing the grid test.
                pass
        position.iloc[t] = int(current_invested)

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
