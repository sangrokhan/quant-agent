"""Strategy: RSI UlcerShield-style multi-layer RSI Threshold portfolio.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-139):
Per https://ulcershield.substack.com/p/rsi-ulcershield-system-rules-and-structure
(William Michael DeJonge, "RSI UlcerShield System - Rules and Structure",
May 2026; visited via browser_exec direct URL fetch -- web_search DDGS
backend gave no useful direct source this iteration), the disclosed system
runs FIVE independent RSI "layers" in parallel rather than one single RSI
signal:

    "The system consists of five RSI PriceSolver(TM) layers:
    QQQ / QLD -- RSI periods: 2, 3, 5, 8, 13 -- thresholds: 30, 30, 30, 30, 34
    Capital is allocated equally across all layers ... enter when any layer
    triggers a long condition at the close ... exit when the corresponding
    RSI layer triggers an exit condition ... Positions unwind progressively
    as layers deactivate."

The source's own claimed outcome: applying this multi-layer structure to
QQQ over its backtest period improved Ulcer Index from 44.44 (buy-and-hold)
to 2.40 and cut max closed drawdown from 82.97% to 17.62%, while modestly
IMPROVING CAGR (9.51% -> 10.83%) versus buy-and-hold -- the claimed benefit
is diversification across RSI timeframes smoothing the equity curve, not
raw alpha.

Since the source's site (RSI PriceSolver(TM)/UlcerShield.com) paywalls the
EXACT numeric exit-threshold value per layer (only entry thresholds are
disclosed; the article states RSI Threshold is a "single-layer, close-based
boundary system" implying ONE boundary per layer, not separate entry/exit
levels), this implementation uses the standard single-boundary RSI
mean-reversion convention already established elsewhere in this repo:
layer i is LONG when RSI(period_i) < threshold_i at close, and FLAT when
RSI(period_i) >= threshold_i (i.e. entry and exit share the same boundary,
a symmetric close-based crossing). Position size for each layer is 1/N of
capital, N=len(periods), summed across all currently-active layers (a
{0, 1/5, 2/5, 3/5, 4/5, 1} fractional exposure series rather than the
usual {0,1} binary -- this repo's first multi-layer FRACTIONAL-exposure
RSI portfolio, distinct from every single-RSI-signal strategy already
tested (plain RSI(2), Connors RSI, RMI, Cumulative RSI, QS RSI, etc., all
{0,1} binary position series).

Source: https://ulcershield.substack.com/p/rsi-ulcershield-system-rules-and-structure

Interface contract for validators/grid_test:
    generate_signals(price_df, **params) -> pd.Series  (fractional [0,1] exposure)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    periods: tuple = (2, 3, 5, 8, 13),
    thresholds: tuple = (30.0, 30.0, 30.0, 30.0, 34.0),
) -> pd.Series:
    """Return a fractional [0,1] exposure series (sum of active-layer weights)."""
    df = _prep(price_df)
    close = df["close"]
    n_layers = len(periods)
    weight_per_layer = 1.0 / n_layers

    exposure = pd.Series(0.0, index=close.index)
    for period, threshold in zip(periods, thresholds):
        rsi = _rsi(close, period)
        layer_long = (rsi < threshold).astype(float)
        exposure = exposure + layer_long * weight_per_layer

    return exposure


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = exposure.shift(1).fillna(0) * daily_ret
    return strategy_ret
