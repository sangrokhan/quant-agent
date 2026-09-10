"""Strategy: ROC momentum entry with an adaptive ATR-ratcheting trailing stop exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-014):
Per Bui & Nguyen, "Systematic Trend-Following with Adaptive Portfolio
Construction: Enhancing Risk-Adjusted Alpha in Cryptocurrency Markets"
(arXiv:2602.11708, https://arxiv.org/abs/2602.11708 / full text
https://arxiv.org/html/2602.11708, visited this iteration): the paper's
"AdaptiveTrend" signal generation module (Section 3.2, fully disclosed
formula) uses (1) a momentum entry: MOM_t = (P_t - P_{t-L}) / P_{t-L} (a
plain rate-of-change over lookback L), triggering a long entry when
MOM_t > theta_entry, and (2) a dynamic trailing stop exit:
S_t = max(S_{t-1}, P_t - alpha * ATR_t(k)) -- a monotonically-ratcheting
ATR-scaled trailing stop (never lowers), closing the position when
P_t < S_t. The paper reports (on 6-hour crypto bars, 150+ pairs,
2022-2024) an annualized Sharpe of 2.41 and MDD of -12.7% for the full
multi-asset portfolio framework; this repo tests the SIGNAL GENERATION
MODULE in isolation (Eq. 2-3, the only fully mechanical single-asset
piece) on daily bars for both equity and crypto, since this repo's
data/loaders.py + grid_test.py infrastructure is single-asset/daily-bar
oriented and does not support the paper's monthly cross-sectional
portfolio-selection/asymmetric-70/30-allocation machinery (out of scope).

Distinct from this repo's existing dual-timeframe ROC breakout entry
(2026-09-04-092, which uses a rolling-extreme breakout trigger plus a
FIXED ATR-multiple stop-loss) because this strategy uses (1) a single
plain ROC threshold-crossing entry (no breakout condition, no dual
timeframe) and (2) a MONOTONICALLY RATCHETING ATR trailing stop that only
tightens toward price on favorable moves (Chandelier-Exit-style
mechanics) rather than a fixed static stop-loss set once at entry.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

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
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(period).mean()


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 20,
    entry_threshold: float = 0.03,
    atr_period: int = 14,
    atr_mult: float = 3.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    mom = (close - close.shift(lookback)) / close.shift(lookback)
    atr = _atr(high, low, close, atr_period)

    entry_signal = mom > entry_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    stop_level = None

    for i in range(len(close)):
        price = close.iloc[i]
        if in_position:
            candidate_stop = price - atr_mult * atr.iloc[i] if pd.notna(atr.iloc[i]) else stop_level
            if candidate_stop is not None and stop_level is not None:
                stop_level = max(stop_level, candidate_stop)
            elif candidate_stop is not None:
                stop_level = candidate_stop

            if stop_level is not None and price < stop_level:
                in_position = False
                stop_level = None
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]) if pd.notna(entry_signal.iloc[i]) else False:
                in_position = True
                init_stop = price - atr_mult * atr.iloc[i] if pd.notna(atr.iloc[i]) else None
                stop_level = init_stop
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
