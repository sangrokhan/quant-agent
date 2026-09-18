"""Strategy: Gold Long-Only Gated by 10-Year Treasury Yield Easing Regime.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-102):
Per enlightenedstocktrading.com's "Gold and Interest Rates: The Intermarket
Signal That Halved Gold's Drawdown" (https://enlightenedstocktrading.com/gold-and-interest-rates/,
Adrian Reid): gold pays no yield, so the opportunity cost of holding it
rises with interest rates; holding gold only when the 10-year Treasury
yield is in an "easing" (falling/low) regime should reduce drawdowns
relative to a gold buy-and-hold. Article's own headline finding (rules not
disclosed -- "system is now in incubation"): full-period gold drawdown
45.6% cut to 22.5% (less than half) by only holding gold when the 10Y yield
regime says so, at some, disclosed-as-nonzero, cost to raw CAGR. We
implement our own mechanical operationalization of the *concept* (10Y yield
trend regime, not the article's proprietary undisclosed exact rule) since
the exact numeric thresholds are gated.

Distinct from the two most closely-related prior strategies in this repo:
 - 2026-09-09-051 (TNX crossing below its own 25d SMA as a risk-on BUY
   signal for the S&P 500/SPY) -- same underlying indicator direction
   (TNX vs its own SMA) but applied to a completely different asset (SPY,
   equities) under a completely different economic rationale (looser
   financial conditions -> risk-on equities), not gold's opportunity-cost
   mechanism.
 - 2026-09-11-059 (TIP uptrend as a real-yield PROXY gate on GLD) -- uses
   TIP (an ETF price) as an indirect proxy for real yields, not the 10-year
   nominal Treasury yield (^TNX) directly.
This strategy is the first to gate GLD directly on ^TNX's own trend
(nominal yield, not TIPS-implied real yield, not applied to equities).

Signal logic
------------
- tnx_trend[t] = ^TNX close relative to its own rolling SMA(tnx_ma_window)
  (default 200 -- a "regime", not a fast oscillator, per the source's own
  emphasis that "interest rates do not flip direction every week... central
  banks move in cycles that last years").
- Long GLD when ^TNX.close[t] < tnx_trend[t] * ma_threshold_ratio (default
  1.0 -- yield below its own long-run trend = easing regime).
- Flat otherwise.
- No stop-loss, no additional filter -- matches the source's simple
  single-signal design description ("only holds gold when rates are in an
  easing phase, the rest of the time it sits in cash").

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

NOTE: `price_df` is expected to be GLD's own price frame; the ^TNX series is
fetched internally via `data/loaders.py::load_equity` bounded to the same
date range, matching the established pattern used by
`2026-09-18_move_index_lowvol_tlt_regime.py` for auxiliary-series strategies.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_tnx_series(index: pd.DatetimeIndex) -> pd.Series:
    """Fetch ^TNX close series aligned (ffilled) to the given index."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    tnx_df = load_equity("^TNX", start, end)
    tnx_df = _prep(tnx_df)
    aligned = tnx_df["close"].reindex(index, method="ffill").bfill()
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    tnx_ma_window: int = 200,
    ma_threshold_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series for GLD.

    Long when ^TNX (10Y Treasury yield) is below `ma_threshold_ratio` times
    its own trailing SMA (an easing-regime proxy); flat otherwise.
    """
    df = _prep(price_df)
    close = df["close"]

    tnx_close = _get_tnx_series(close.index)
    tnx_sma = tnx_close.rolling(tnx_ma_window, min_periods=20).mean()

    easing_regime = tnx_close < (tnx_sma * ma_threshold_ratio)
    position = easing_regime.fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
