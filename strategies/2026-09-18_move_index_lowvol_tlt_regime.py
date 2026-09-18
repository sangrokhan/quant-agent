"""Strategy: Bond MOVE Index Low-Volatility Regime Filter (long TLT only in calm bond-vol regimes).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-099):
Per quantifiedstrategies.com's "Bond MOVE Index and TLT Trading Strategy"
(https://www.quantifiedstrategies.com/bond-move-index-tlt-strategy/): the
MOVE index (bond-market analog of VIX) rising above its historical mean
signals elevated rate-volatility that is bad for holding long-duration
Treasuries; avoiding those high-MOVE periods and holding TLT only when MOVE
is below its trailing rolling mean reduces max drawdown roughly in half vs
buy-and-hold (source's own numbers: CAGR 2.80% vs buy&hold 4.33%, MDD 21.34%
vs buy&hold 44.14%, ~60% time in market). Source's own conclusion is
lukewarm on absolute CAGR but notes the drawdown reduction is the real
value-add -- we test whether the risk-adjusted (Sharpe) profile clears this
repo's acceptance bar.

Distinct from the only prior MOVE-index strategy in this repo
(2026-09-05-043, `move_index_panic_regime.py`): that strategy uses a MOVE
*panic-spike* (crossing ABOVE a high threshold) as a contrarian BUY signal
for equities (SPY) with a 200d-SMA trend filter. This strategy instead uses
a MOVE *below-average* condition as a simple regime-avoidance HOLD filter
for the bond ETF itself (TLT), with no contrarian/trend-filter logic and no
equities involved at all -- opposite direction, opposite asset, opposite
mechanism.

Signal logic
------------
- move_rolling_mean[t] = MOVE.close rolling mean over `move_lookback` days
  (source uses a long-run historical mean around 85-86; we use a rolling
  window so the strategy is testable across arbitrary sub-periods without
  hardcoding a fixed historical constant).
- Long TLT when MOVE.close[t] <= move_rolling_mean[t] * vol_threshold_ratio
  (source's discussion: full 1x mean threshold "leaves the strategy with
  very little time in the market" if set too tight, hence the ratio knob).
- Flat otherwise (avoid TLT during elevated bond-vol regimes).
- No trend filter, no stop-loss -- matches source's simple avoid-high-vol
  design.

Data note: the MOVE index (^MOVE) is fetched via `data/loaders.py`'s
`load_equity` helper (yfinance ticker "^MOVE"), then merged onto the TLT
price series to build the position signal -- TLT is the tradable instrument.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

NOTE: because this strategy needs an auxiliary series (^MOVE) beyond the
single `price_df` the grid-test/validator harness passes in, `price_df` here
is expected to BE the TLT price frame; the MOVE series is fetched internally
via `data/loaders.py::load_equity("^MOVE", ...)` bounded to price_df's own
date range, so this still satisfies the required `generate_signals(price_df,
**params)` / `generate_returns(price_df, **params)` keyword-only contract
(no extra positional args) even though it does one extra internal fetch.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_move_series(index: pd.DatetimeIndex) -> pd.Series:
    """Fetch ^MOVE close series aligned (ffilled) to the given index."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    move_df = load_equity("^MOVE", start, end)
    move_df = _prep(move_df)
    move_close = move_df["close"]
    # Align to the TLT trading calendar (forward-fill for any gaps).
    aligned = move_close.reindex(index, method="ffill")
    aligned = aligned.bfill()
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    move_lookback: int = 252,
    vol_threshold_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series for TLT.

    Long when MOVE is at or below `vol_threshold_ratio` times its own
    trailing rolling mean (calm bond-vol regime); flat otherwise.
    """
    df = _prep(price_df)
    close = df["close"]

    move_close = _get_move_series(close.index)
    move_rolling_mean = move_close.rolling(move_lookback, min_periods=20).mean()

    calm_regime = move_close <= (move_rolling_mean * vol_threshold_ratio)
    position = calm_regime.fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
