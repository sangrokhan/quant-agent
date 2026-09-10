"""Strategy: Regional bank stocks (KRE) SMA trend-following gated by a
yield-curve steepening proxy (TLT/IEF duration ratio downtrend).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per marketwise.com's "Yield Curve Steepening 2026" (visited this iteration
via browser_exec fallback): "Banks live on the spread between what they pay
for money (short-term deposit rates, anchored to the Fed) and what they earn
lending it (longer-term loan and mortgage rates). A steeper curve widens that
spread -- the net interest margin -- which is why bank stocks ... historically
outperform during sustained [steepening]." Regional banks (KRE) are more
balance-sheet/NIM-sensitive than money-center banks, making them the purest
single-ETF proxy for this effect.

This repo has no direct 10Y-2Y Treasury yield spread feed via data/loaders.py
(yfinance/ccxt OHLCV only), but the already-validated TLT/IEF price-ratio
construction (2026-09-11-045, "duration ratio is the dominant driver...
curve-shape changes... produce additional but smaller effects", per
ConvexTrade) is repurposed here as a steepening proxy: when the LONG end
(TLT, 20+yr) underperforms the INTERMEDIATE end (IEF, 7-10yr) -- i.e. the
TLT/IEF ratio is in a downtrend / below its own SMA -- long-end yields are
rising faster than intermediate yields, consistent with curve steepening
at the back end. Gate: long KRE's own SMA(trend_sma_window) trend-following
signal only when TLT/IEF ratio is BELOW its own ratio_sma_window-day SMA
(bear/curve-steepening proxy, favorable NIM regime for banks); flat
otherwise.

First KRE-based and first bank-sector-NIM strategy in this repo, and the
first application of the TLT/IEF ratio in the "steepening" (ratio DOWN)
direction rather than the "flight-to-duration" (ratio UP) direction used by
2026-09-11-045 on QQQ/SPY -- economically the two hypotheses are opposite
regimes of the same signal, tested here on an asset (KRE) hypothesized to
benefit from the OPPOSITE macro state.

Interface contract for validators (see validation/validators.py) /
grid_test.py (see validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

Note: generate_signals/generate_returns internally load TLT and IEF via
data/loaders.py (same "internal basket load" pattern as this repo's other
cross-asset ratio gates, e.g. 2026-09-11-045/054/058/059).
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_ratio_regime(
    index: pd.DatetimeIndex,
    ratio_sma_window: int,
) -> pd.Series:
    """Load TLT/IEF and return a boolean Series aligned to `index`:
    True when TLT/IEF ratio is BELOW its own SMA (steepening/bear regime)."""
    from loaders import load_equity  # data/loaders.py

    start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
    end = index.max().to_pydatetime() if len(index) else datetime.now()

    tlt = _prep(load_equity("TLT", start, end))["close"]
    ief = _prep(load_equity("IEF", start, end))["close"]

    ratio = (tlt / ief).reindex(index).ffill()
    ratio_sma = ratio.rolling(ratio_sma_window).mean()
    steepening_regime = ratio < ratio_sma
    return steepening_regime.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    trend_sma_window: int = 50,
    ratio_sma_window: int = 50,
    invert_signal: bool = False,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long only when: close > SMA(trend_sma_window) (primary asset trend
    filter) AND TLT/IEF ratio is below (steepening) or above (invert_signal)
    its own ratio_sma_window-day SMA.
    """
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_sma_window).mean()
    trend_ok = close > sma

    steepening_regime = _load_ratio_regime(df.index, ratio_sma_window)
    regime_ok = (~steepening_regime) if invert_signal else steepening_regime

    position = (trend_ok & regime_ok).astype(int)
    return position.rename("position")


def generate_returns(
    price_df: pd.DataFrame,
    trend_sma_window: int = 50,
    ratio_sma_window: int = 50,
    invert_signal: bool = False,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        trend_sma_window=trend_sma_window,
        ratio_sma_window=ratio_sma_window,
        invert_signal=invert_signal,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret.rename("returns")
