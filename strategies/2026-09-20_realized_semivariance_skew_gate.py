"""Strategy: Realized Semivariance Skew (Good-Volatility vs Bad-Volatility
Asymmetry) regime gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-101):
Per Barndorff-Nielsen, Kinnebrock & Shephard (2010, "Measuring downside
risk - realised semivariance", Harvard/Oxford working paper, read this
iteration via Google SERP) and Patton & Sheppard (2015, "Good Volatility,
Bad Volatility: Signed Jumps and the Persistence of Volatility", Review of
Economics and Statistics -- summarized via RePEc/arXiv snippets this
iteration): daily realized variance can be decomposed into an "upside"
(good) realized semivariance RSV+ = sum of squared POSITIVE intraday-proxy
returns, and a "downside" (bad) realized semivariance RSV- = sum of squared
NEGATIVE intraday-proxy returns, with RV = RSV+ + RSV-. The literature's
key finding: bad (downside) volatility is more persistent and more
predictive of future negative returns than good (upside) volatility --
periods where RSV- dominates RSV+ (i.e. a negative "semivariance skew")
tend to precede continued weakness, while periods where RSV+ dominates
(positive skew, "good vol regime") are more benign.

This repo's existing downside-risk-sizing family (Sortino/Downside-
Deviation/Kappa-3, ids 2026-09-13-048/059/061) all use semi-deviation as a
denominator in a continuous inverse-risk SIZING dial on top of an existing
SMA trend gate. This strategy is architecturally distinct: it uses the
SIGN/RATIO of the semivariance SKEW itself (RSV+ - RSV-)/(RSV+ + RSV-),
trailing-averaged over a window, as a standalone binary regime FILTER
(long only while the trailing skew is non-negative -- good vol regime;
flat when negative -- bad vol regime dominates), with no separate trend/
SMA gate and no continuous position sizing. Adapted to this repo's daily-
bar-only data (no true intraday tick data): the "semivariance" proxy here
is computed from the split of each day's own close-to-close return into
positive vs negative squared contributions over a trailing window (not a
true intraday high-frequency decomposition, since data/loaders.py provides
OHLC bars only) -- a coarser daily-frequency analog of the same signed-jump
asymmetry concept.

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


def _semivariance_skew(close: pd.Series, window: int) -> pd.Series:
    ret = close.pct_change()
    pos_sq = (ret.clip(lower=0) ** 2)
    neg_sq = (ret.clip(upper=0) ** 2)
    rsv_pos = pos_sq.rolling(window).sum()
    rsv_neg = neg_sq.rolling(window).sum()
    total = rsv_pos + rsv_neg
    skew = (rsv_pos - rsv_neg) / total.replace(0, pd.NA)
    return skew


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 20,
    skew_threshold: float = 0.0,
) -> pd.Series:
    """Long (1) while trailing realized-semivariance skew >= skew_threshold
    (good/upside volatility dominates), flat (0) otherwise (bad/downside
    volatility dominates)."""
    df = _prep(price_df)
    close = df["close"]
    skew = _semivariance_skew(close, window=window)
    position = (skew >= skew_threshold).astype(int)
    position = position.where(~skew.isna(), 0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
