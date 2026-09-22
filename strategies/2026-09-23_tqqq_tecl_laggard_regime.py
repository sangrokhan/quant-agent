"""Strategy: 3-Day Laggard Rotation between TQQQ/TECL, gated by a QQQ trend
regime filter (simplified single-leg adaptation, defensive sleeve = cash).

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration's id):
Per FinLab's "Short-Term Mean Reversion Trading Strategy Backtest: The 3-Day
Laggard Rule Behind a 67% CAGR"
(https://finlab.finance/en/blog/us-mean-reversion-strategy), a fully
disclosed 3-layer rule: (1) risk-on regime when QQQ is above its 200-day SMA
AND its 126-day (6-month) return is positive; (2) in risk-on, hold whichever
of TQQQ or TECL (two heavily-overlapping 3x-leveraged growth ETFs) LAGGED
over the trailing 3 trading days (short-term reversal/laggard-catch-up bet,
liquidity-provision mechanism per Da/Liu/Schaumburg 2014); (3) in risk-off,
rotate to a defensive sleeve (source: strongest of IEF/GLD/SHY by momentum).
Source's own published stats: 2016-2026 backtest CAGR 67.4%, Sharpe 1.43,
max drawdown -27.6% (vs naive TQQQ/TECL buy-and-hold drawdowns of -78% to
-82%), with an out-of-sample confirmation (2022-2026, parameters fixed from
2016-2021) showing an even HIGHER out-of-sample CAGR (75.7%) at a similar
Sharpe -- a genuine walk-forward-style validation already performed by the
source itself. Source is explicit that the reversal/laggard tilt itself is
statistically weak (t-stat 1.33) and most of the return comes from the
regime-timing (holding 3x leverage only when QQQ's trend/momentum agree).

Framework adaptation note: this repo's generate_signals/generate_returns
contract (see strategies/2026-09-08_pairs_zscore_cointegration.py for
established precedent) takes a single ``price_df`` (the traded asset, TQQQ)
plus **params. The QQQ regime-filter series and the TECL comparison leg are
fetched internally via data/loaders.py, keyed off ``price_df``'s own date
range, following the same "fetch a partner leg internally" pattern already
used in this repo's pairs-trading strategy. The defensive sleeve (source's
IEF/GLD/SHY momentum rotation, a 3RD/4TH asset selection layer) is
SIMPLIFIED to flat/cash here (rather than rotating into another asset) to
stay within the single-traded-asset 0/1 position-series convention used
throughout this repo -- this is a conservative simplification (foregoing
defensive-sleeve carry, not adding leverage), consistent with how the repo
has handled other multi-asset source strategies (e.g. 2026-09-22-125's
"single-asset exposure dial" note). First strategy in this repo combining a
leveraged-ETF regime-timing gate with a genuine SECOND-INSTRUMENT
laggard-vs-leader reversal signal (distinct from all prior pairs/spread
z-score strategies, which trade the SPREAD directly rather than choosing
which of two correlated legs to hold).

Signal logic
------------
- Regime filter (on QQQ): close > SMA(200) AND 126-day return > 0 -> risk-on.
- Laggard signal (TQQQ price_df vs TECL partner leg): compute each asset's
  own trailing 3-day return; hold TQQQ (position=1) when TQQQ's 3-day return
  is LOWER than TECL's (TQQQ is the laggard) AND risk-on; flat otherwise
  (when TQQQ is the leader, or risk-off, the position simplification holds
  cash rather than switching into TECL, since this repo's single-symbol
  contract can only express a position in the ``price_df`` asset itself).
- Exit / flat: risk-off (QQQ regime breaks) OR TQQQ becomes the leader
  (3-day return >= TECL's).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_series(index: pd.DatetimeIndex, symbol: str, asset_class: str = "equity") -> pd.Series:
    """Fetch a comparison symbol's close series over price_df's date range."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity, load_crypto  # noqa: E402

    start = index.min() - timedelta(days=400)  # extra lookback for the 200d/126d regime calc
    end = index.max() + timedelta(days=2)
    if asset_class == "crypto":
        df = load_crypto(symbol, start, end)
    else:
        df = load_equity(symbol, start, end)
    df = _prep(df)
    return df["close"]


def generate_signals(
    price_df: pd.DataFrame,
    partner_symbol: str = "TECL",
    regime_symbol: str = "QQQ",
    trend_sma: int = 200,
    momentum_window: int = 126,
    laggard_window: int = 3,
) -> pd.Series:
    """Return a {0,1} position series: hold TQQQ (price_df) only when it is
    the 3-day laggard vs. partner_symbol AND the QQQ regime filter is risk-on."""
    df = _prep(price_df)
    close = df["close"]

    partner_close = _load_series(df.index, partner_symbol, "equity")
    regime_close = _load_series(df.index, regime_symbol, "equity")

    partner_close = partner_close.reindex(close.index, method="ffill")
    regime_close = regime_close.reindex(
        regime_close.index.union(close.index), method="ffill"
    ).reindex(close.index, method="ffill")

    regime_sma = regime_close.rolling(trend_sma, min_periods=trend_sma).mean()
    regime_mom = regime_close.pct_change(momentum_window)
    risk_on = (regime_close > regime_sma) & (regime_mom > 0)

    own_ret = close.pct_change(laggard_window)
    partner_ret = partner_close.pct_change(laggard_window)
    is_laggard = own_ret < partner_ret

    valid = regime_sma.notna() & regime_mom.notna() & own_ret.notna() & partner_ret.notna()

    position = (risk_on & is_laggard & valid).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    partner_symbol: str = "TECL",
    regime_symbol: str = "QQQ",
    trend_sma: int = 200,
    momentum_window: int = 126,
    laggard_window: int = 3,
) -> pd.Series:
    """Return daily strategy returns (position held from signal close to next bar close)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        partner_symbol=partner_symbol,
        regime_symbol=regime_symbol,
        trend_sma=trend_sma,
        momentum_window=momentum_window,
        laggard_window=laggard_window,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(int) * daily_returns
    return strat_returns
