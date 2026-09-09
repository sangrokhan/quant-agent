"""Strategy: Yield-Curve Un-Inversion Bear Signal + 200-day SMA Trend Filter
(drawdown-control variant of 2026-09-05-024).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
2026-09-05-024 (yield-curve un-inversion bear signal: default long, flat for
flat_window_days after the 10Y-3M Treasury spread un-inverts) was a STRONG
near-miss -- Sharpe/TC-survival/param-sensitivity all passed decisively on
QQQ and SPY (grid pass_fraction 33.3%, best of any strategy tested in this
repo at the time), but max_drawdown failed on both symbols (QQQ decisively
35.6% vs 25% budget; SPY marginally 25.4% vs 25.0%, a 0.4pp miss). The
original construction is long-by-default at ALL times except a short
post-un-inversion flat window -- meaning it stays long straight through the
INITIAL decline that precedes the eventual un-inversion event (e.g. 2022's
slow bleed before the curve un-inverted in 2024), which is exactly where
the drawdown accumulates. This iteration adds a standard 200-day SMA trend
filter as an ADDITIONAL gate on top of the original un-inversion flat-window
logic (unchanged) specifically to address that prior rejection reason: long
only when BOTH (a) price is above its 200d SMA (already in an uptrend, so
we're not holding through the initial leg of a bear market) AND (b) not
within the post-un-inversion flat window. This directly targets the
documented near-miss failure mode (MDD) while keeping the original
yield-curve-timing mechanism intact, rather than being a from-scratch new
hypothesis.

Signal logic
------------
- Fetches ^TNX (10Y) and ^IRX (3M) via data/loaders.py load_equity
  internally, same as 2026-09-05-024.
- Same un-inversion flat-window logic as 2026-09-05-024 (flat for
  flat_window_days trading days after spread crosses from negative to
  >= uninvert_threshold, having been inverted within lookback_days).
- NEW: additionally require close > SMA(trend_window) on the traded asset
  itself to be long; otherwise flat (trend filter, independent of the
  yield-curve state).
- Long only when BOTH the trend filter and the (not-in-flat-window)
  condition are true.

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_yield_spread(idx: pd.DatetimeIndex) -> pd.Series:
    """Fetch ^TNX and ^IRX and return the 10Y-3M spread reindexed/ffilled
    onto the strategy's own trading-day index."""
    from loaders import load_equity

    start = (idx.min() - pd.Timedelta(days=30)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()

    tnx = load_equity("^TNX", start, end)
    irx = load_equity("^IRX", start, end)

    tnx = tnx.set_index("timestamp")["close"].sort_index()
    irx = irx.set_index("timestamp")["close"].sort_index()

    spread = (tnx - irx).sort_index()
    spread.index = spread.index.tz_localize(None) if spread.index.tz is not None else spread.index

    target_idx = idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx
    spread = spread.reindex(spread.index.union(target_idx)).sort_index().ffill()
    spread = spread.reindex(target_idx)
    spread.index = idx
    return spread


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 60,
    uninvert_threshold: float = 0.0,
    flat_window_days: int = 20,
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long only when (a) price is above its own SMA(trend_window) AND (b) not
    within flat_window_days trading days after a yield-curve un-inversion
    event (10Y-3M spread crossing from negative to >= uninvert_threshold,
    having been inverted within the trailing lookback_days).
    """
    df = _prep(price_df)
    idx = df.index
    close = df["close"]

    sma_trend = close.rolling(trend_window).mean()
    trend_ok = (close.shift(1) > sma_trend.shift(1)).fillna(False)

    try:
        spread = _get_yield_spread(idx)
    except Exception:
        # Data unavailable (e.g. crypto symbols) -- fall back to pure
        # trend-following (yield-curve overlay becomes a no-op), correctly
        # showing whatever edge (if any) the trend filter alone has rather
        # than crashing the grid.
        position = trend_ok.astype(int)
        position.name = "position"
        return position

    was_inverted_recently = (spread < 0).rolling(lookback_days, min_periods=1).max().astype(bool)
    is_uninverted_now = spread >= uninvert_threshold
    prev_was_inverted = was_inverted_recently.shift(1).fillna(False)
    uninvert_event = is_uninverted_now & prev_was_inverted & ~(spread.shift(1) >= uninvert_threshold).fillna(False)

    in_flat_window = pd.Series(False, index=idx)
    event_positions = [i for i, v in enumerate(uninvert_event.values) if v]
    for pos in event_positions:
        start_i = pos + 1
        end_i = min(pos + 1 + flat_window_days, len(idx))
        in_flat_window.iloc[start_i:end_i] = True

    position = (trend_ok & ~in_flat_window).astype(int)
    position.name = "position"
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Shift position by 1 day: yesterday's signal determines today's exposure
    # (avoid look-ahead bias -- can't trade on today's own close).
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    strategy_ret.name = "returns"
    return strategy_ret
