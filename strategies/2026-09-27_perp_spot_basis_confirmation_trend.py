"""Strategy: BTC Perpetual-Spot Basis Momentum (regime confirmation, not
mean-reversion).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-006):
Per Google AI-overview synthesis of SSRN/QuantInsti sources on "Bitcoin
Perpetual Futures Basis Premium": the perpetual-to-spot basis
(perp_close - spot_close) / spot_close structurally oscillates around a
small positive mean during bull regimes (driven by leveraged-long demand
paying funding) and turns persistently negative during bear/de-risking
regimes (leveraged shorts paying funding, or simply less aggressive long
positioning). This repo's existing funding-rate strategies (accepted
2026-09-20-031 continuous-sizing-dial; rejected 2026-09-02-001 binary
threshold) use ccxt's `fetch_funding_rate_history()` endpoint directly.
This strategy instead uses a DIFFERENT, independently-fetchable data
source verified feasible this iteration: `data/loaders.py`'s existing
`load_crypto()` helper already fetches OHLCV for BOTH the spot symbol
(`BTC/USDT`) and the linear-perpetual symbol (`BTC/USDT:USDT`) via the
same ccxt Binance provider with no new plumbing required. The basis level
computed purely from these two OHLCV series (no funding-rate endpoint
involved) is used here as a REGIME-CONFIRMATION filter on top of a plain
SMA trend signal (this repo's established kill-switch/gate pattern, e.g.
accepted 2026-09-22-002, 2026-09-22-108, and this trigger's own accepted
2026-09-27-002): only stay long the SMA-trend signal while the basis
remains above its own trailing rolling-mean threshold (confirming
bullish leveraged positioning); flatten when the basis falls below,
even if the SMA trend is still nominally bullish (an early risk-off
signal from derivatives positioning, independent of and preceding
spot price action).

First strategy in this repo using the spot-vs-perpetual-OHLCV basis
(rather than the funding-rate endpoint) as a signal input.

Signal logic
------------
- basis[t] = (perp_close[t] - spot_close[t]) / spot_close[t]
- basis_ma[t] = rolling mean of basis over `basis_window` days
- base trend signal: spot_close > SMA(spot_close, trend_window)
- confirmed long: base trend signal AND basis[t] >= basis_ma[t] *
  confirm_ratio (basis not meaningfully below its own recent average,
  i.e. leveraged positioning still supportive)
- flat otherwise

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)

Note on interface: `price_df` here is the SPOT price_df (the tradable
instrument, matching this repo's grid-test loader convention of one
symbol per asset class); the perpetual series is fetched internally via
`data/loaders.py::load_crypto` using the same date range as `price_df`,
mirroring the established cross-asset-lookup pattern used by
`2026-09-18_move_index_lowvol_tlt_regime.py` (which fetches ^MOVE
alongside TLT). Equity symbols have no perpetual-futures analog, so this
strategy is crypto-only by construction -- the grid test still runs the
equity leg for completeness/falsification (an all-flat or degenerate
equity result is the correct, informative outcome there).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


_PERP_SYMBOL_BY_SPOT = {
    "BTC/USDT": "BTC/USDT:USDT",
    "ETH/USDT": "ETH/USDT:USDT",
}


def _fetch_perp_aligned(spot_df: pd.DataFrame, spot_symbol: str) -> pd.Series | None:
    """Fetch the linear-perpetual OHLCV series and align it to spot_df's index.

    Returns None if the perpetual counterpart cannot be resolved/fetched
    (e.g. an equity symbol with no perpetual-futures analog), signalling
    the caller to treat this as a no-signal / all-flat case.
    """
    perp_symbol = _PERP_SYMBOL_BY_SPOT.get(spot_symbol)
    if perp_symbol is None:
        return None
    try:
        from data.loaders import load_crypto
    except ImportError:
        return None

    idx = spot_df.index
    start = idx.min()
    end = idx.max()
    # load_crypto expects naive/py datetimes; strip tz info for the call,
    # ccxt handles UTC internally regardless.
    start_dt = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
    end_dt = datetime(end.year, end.month, end.day, tzinfo=timezone.utc)
    try:
        perp_df = load_crypto(perp_symbol, start_dt, end_dt, interval="1d")
    except Exception:
        return None
    perp_df = _prep(perp_df)
    perp_close = perp_df["close"].reindex(idx, method="ffill")
    return perp_close


def generate_signals(
    price_df: pd.DataFrame,
    spot_symbol: str = "BTC/USDT",
    trend_window: int = 120,
    basis_window: int = 40,
    confirm_ratio: float = 1.3,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window, min_periods=trend_window).mean()
    base_signal = (close > sma).fillna(False)

    perp_close = _fetch_perp_aligned(df, spot_symbol)
    if perp_close is None:
        # No perpetual-futures analog available (e.g. equity symbol) --
        # mechanically infeasible, correctly return an all-flat series.
        return pd.Series(0, index=close.index, dtype=int)

    basis = (perp_close - close) / close
    basis_ma = basis.rolling(basis_window, min_periods=basis_window).mean()

    confirmed = (basis >= basis_ma * confirm_ratio).fillna(False)

    position = (base_signal & confirmed).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
