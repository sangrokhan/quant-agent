"""Strategy: TRIX Zero-Line Rejection continuation signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-012):
Per Trade-Charts.net's TRIX guide
(https://trade-charts.net/indicators/trix-indicator, browser_exec fetch
after web_extract's DDGS backend couldn't extract page content): "In a
strong uptrend, the TRIX will stay above zero. If it pulls back but
'Rejects' (bounces) off the zero-line without crossing into negative
territory, it's a high-probability continuation signal." This is distinct
from the source's own separately-disclosed "Signal Crossovers" rule (plain
TRIX-vs-signal-line cross, already tested many times in this repo, e.g.
2026-09-04-038) -- here the SIGNAL ITSELF is the zero-line-rejection
pattern: TRIX approaches (but never crosses below) zero during a pullback,
then turns back upward while still positive.

Operationalized: within a rolling lookback window, TRIX must (a) have
stayed continuously >= 0 (no zero-line cross at all -- confirms we're
still in the "uptrend regime" the source requires for this pattern to be
meaningful), (b) have dipped down to within `near_zero_pct` of its own
recent local high (i.e. genuinely pulled back close to zero, not just
drifted sideways near an already-high reading), and (c) turned back up on
the current bar (today's TRIX > yesterday's TRIX). Exit when TRIX crosses
below zero (rejection failed / regime broke) or a max_hold_days time-stop.

Distinct from all 3 prior TRIX entries in this repo:
  - 2026-09-04-038: plain TRIX/signal-line crossover + zero-line >0 filter
    (crossover IS the trigger, no pullback/rejection concept).
  - 2026-09-07-018: TRIX bullish divergence vs price (different mechanism
    entirely -- divergence, not a zero-line bounce).
  - 2026-09-09-067: pullback-in-trend gated by an external SMA baseline
    (trend filter is on PRICE, and the trigger is TRIX's own signal-line
    cross after softening -- not a same-indicator zero-line bounce).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _trix(close: pd.Series, period: int) -> pd.Series:
    ema1 = close.ewm(span=period, adjust=False).mean()
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    ema3 = ema2.ewm(span=period, adjust=False).mean()
    trix = 100 * ema3.pct_change()
    return trix


def generate_signals(
    price_df: pd.DataFrame,
    trix_period: int = 14,
    lookback: int = 15,
    near_zero_pct: float = 0.35,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    trix = _trix(close, trix_period)

    # rolling local high of TRIX over the lookback window (used to measure
    # "how close to zero did it pull back relative to its recent peak")
    rolling_high = trix.rolling(lookback).max()
    stayed_nonneg = (trix >= 0).rolling(lookback).min().astype(bool)

    # pulled back close to zero: current trix within near_zero_pct of the
    # distance from the rolling high down to zero (small trix value
    # relative to the recent peak, but still >= 0)
    pulled_back = (trix.abs() <= near_zero_pct * rolling_high.abs().replace(0, np.nan)) & (trix >= 0)
    turned_up = trix.diff() > 0

    setup = stayed_nonneg & pulled_back.shift(1).fillna(False) & turned_up & (trix >= 0)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = -1
    idx_list = df.index.tolist()

    for i in range(1, len(df)):
        ts = idx_list[i]
        if not in_pos:
            if bool(setup.iloc[i]):
                in_pos = True
                entry_idx = i
        else:
            days_held = i - entry_idx
            broke = trix.iloc[i] < 0
            if broke or days_held >= max_hold_days:
                in_pos = False
            else:
                position.loc[ts] = 1

        if in_pos and i >= entry_idx:
            position.loc[ts] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(price_df, **params)
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    return strat_returns
