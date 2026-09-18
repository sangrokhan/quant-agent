"""Strategy: Nick Radge Weekend Trend Trader (weekly-bar breakout + regime
filter + asymmetric trailing stop).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per the ThinkorSwim code posted at usethinkscript.com
(https://usethinkscript.com/threads/weekend-trend-trader-by-nick-radge-strategy-for-thinkorswim.669/),
Nick Radge's "Weekend Trend Trader" system (fully disclosed numeric rule,
resolving the earlier "paywalled" concern noted in this repo's
2026-09-11-088) is: on a WEEKLY timeframe, scanned Friday after close --
(1) ENTRY: stock makes a new 20-week high AND the market (index) closes
above its own 10-week SMA (broad regime filter) AND the 20-week
Rate-of-Change is > 30% (strong momentum confirmation); buy at Monday's
open. (2) EXIT: an asymmetric trailing stop -- while the market regime is
UP (index > its 10-week SMA), the stop trails 40% below the recent 20-week
high; if the market regime flips DOWN, the stop tightens to 10% below the
recent high (protect gains faster in a downturn); stops only ratchet up,
never down; exit at Monday's open when triggered.

This repo's single-symbol data/loaders.py architecture has no genuine
per-stock "index membership" concept (the source's original design scans
a broad stock universe against SPX/NDX/RUT/DJX), so -- consistent with how
this repo's existing dual-momentum/basket-gate strategies handle
cross-asset regime filters -- the regime filter here uses the SAME traded
asset's own 10-week SMA as its own market-regime proxy (self-referential
regime filter: "is this asset itself in an uptrend on its own weekly
chart", a standard simplification when a genuine external index reference
isn't available). This differs from and directly tests the entry/stop
MECHANICS (new-high breakout + ROC confirmation + asymmetric ATR-free
percentage trailing stop) independent of the multi-index cross-sectional
universe-scanning aspect (which remains infeasible, per 2026-09-11-088).

Signal logic (weekly bars, resampled from the daily OHLCV this repo's
data/loaders.py provides)
------------------------------------------------------------------
- Weekly close, weekly high computed by resampling daily bars to
  W-FRI (Friday-ending weeks).
- regime_up = weekly_close > SMA(weekly_close, regime_window) [default 10].
- new_high = weekly_close == rolling max(weekly_close, high_window)
  [default 20 weeks].
- weekly_roc = weekly_close.pct_change(roc_window) [default 20 weeks].
- Entry (long): new_high AND regime_up AND weekly_roc > roc_threshold
  [default 0.30].
- Trailing stop level: recent_high = rolling max(weekly_close, high_window
  - 1) [the "Highest(close,19)" i.e. window-1 in source terms]; loss_pct =
  init_trail_pct [0.40] if regime_up else downtrend_trail_pct [0.10];
  stop_level = recent_high * (1 - loss_pct); stop only ratchets UP (never
  lowered) once in a position.
- Exit: weekly_close <= ratcheted stop_level.
- Position held constant through each week (weekly-bar signal, applied to
  the FOLLOWING week's daily returns via forward-fill, matching the
  source's "signal computed after Friday close, executed Monday open"
  cadence -- approximated here as next-week entry/exit on daily bars).

Sources read this iteration:
- https://usethinkscript.com/threads/weekend-trend-trader-by-nick-radge-strategy-for-thinkorswim.669/
  (full ThinkorSwim source code with all numeric defaults: roc_window=20,
  regime_window=10, high_window=20, roc_threshold=0.30(implied "rate>30"),
  init_trail_pct=0.40, downtrend_trail_pct=0.10).

Distinct from this repo's 2026-09-11-088 (marked infeasible due to the
cross-sectional universe-scan aspect) -- this iteration isolates and tests
the single-symbol entry/exit MECHANICS with a self-referential regime
proxy instead of abandoning the idea outright.

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


def _weekly_signals(
    df: pd.DataFrame,
    regime_window: int,
    high_window: int,
    roc_window: int,
    roc_threshold: float,
    init_trail_pct: float,
    downtrend_trail_pct: float,
) -> pd.Series:
    """Compute the weekly {0,1} position series, forward-filled to daily."""
    weekly_close = df["close"].resample("W-FRI").last().dropna()

    regime_sma = weekly_close.rolling(regime_window).mean()
    regime_up = weekly_close > regime_sma

    rolling_high_full = weekly_close.rolling(high_window).max()
    new_high = weekly_close >= rolling_high_full

    weekly_roc = weekly_close.pct_change(roc_window)

    entry_signal = new_high & regime_up & (weekly_roc > roc_threshold)

    recent_high_lag = weekly_close.rolling(max(1, high_window - 1)).max()
    loss_pct = pd.Series(
        [init_trail_pct if up else downtrend_trail_pct for up in regime_up],
        index=weekly_close.index,
    )
    raw_stop = recent_high_lag * (1 - loss_pct)

    position = pd.Series(0, index=weekly_close.index, dtype=int)
    in_position = False
    ratcheted_stop = None

    for i in range(len(weekly_close)):
        price = weekly_close.iloc[i]
        if not in_position:
            if bool(entry_signal.iloc[i]) if pd.notna(entry_signal.iloc[i]) else False:
                in_position = True
                ratcheted_stop = raw_stop.iloc[i] if pd.notna(raw_stop.iloc[i]) else None
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
        else:
            candidate_stop = raw_stop.iloc[i]
            if pd.notna(candidate_stop):
                ratcheted_stop = candidate_stop if ratcheted_stop is None else max(ratcheted_stop, candidate_stop)
            if ratcheted_stop is not None and price <= ratcheted_stop:
                in_position = False
                ratcheted_stop = None
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1

    return position


def generate_signals(
    price_df: pd.DataFrame,
    regime_window: int = 10,
    high_window: int = 20,
    roc_window: int = 20,
    roc_threshold: float = 0.30,
    init_trail_pct: float = 0.40,
    downtrend_trail_pct: float = 0.10,
) -> pd.Series:
    """Return a {0,1} long/flat DAILY position series (forward-filled from
    the weekly signal, applied on the FOLLOWING trading day per the
    source's Friday-close-decide / Monday-open-execute cadence)."""
    df = _prep(price_df)
    weekly_position = _weekly_signals(
        df, regime_window, high_window, roc_window, roc_threshold,
        init_trail_pct, downtrend_trail_pct,
    )
    # Shift weekly decision by one week (decided Friday, executed next week)
    # then forward-fill onto the daily index.
    weekly_position_shifted = weekly_position.shift(1).fillna(0).astype(int)
    daily_position = weekly_position_shifted.reindex(df.index, method="ffill").fillna(0).astype(int)
    return daily_position


def generate_returns(
    price_df: pd.DataFrame,
    regime_window: int = 10,
    high_window: int = 20,
    roc_window: int = 20,
    roc_threshold: float = 0.30,
    init_trail_pct: float = 0.40,
    downtrend_trail_pct: float = 0.10,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        regime_window=regime_window,
        high_window=high_window,
        roc_window=roc_window,
        roc_threshold=roc_threshold,
        init_trail_pct=init_trail_pct,
        downtrend_trail_pct=downtrend_trail_pct,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
