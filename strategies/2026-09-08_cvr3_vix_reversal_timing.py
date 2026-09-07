"""Strategy: CVR3 VIX Market Timing (Larry Connors & Dave Landry) --
trades an equity index based on VIX's own extension relative to its
10-day moving average.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
per https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/cvr3-vix-market-timing,
excessive VIX spikes (fear extremes) tend to mean-revert, and SPY often
rallies during that VIX reversion. Source's own three-rule BUY signal (all
apply to the VIX index itself, trade is taken on the price index):
(1) VIX daily low > VIX's own 10-day SMA (entire bar above the MA),
(2) VIX close >= 10% above its 10-day SMA (PPO(1,10,1) >= 10),
(3) VIX close < VIX open (a down/filled candle on the VIX itself).
Stop-loss/exit: VIX crosses back below the PRIOR day's 10-day MA
(intraday basis, approximated here as VIX close < prior-day 10d MA), or a
fixed 2-4 day time exit (source's own alternative suggestion). This is the
first strategy in this repo to trade an EQUITY index using a SEPARATE
instrument's (VIX) own signal, distinct from all prior volatility-PROXY
strategies (Williams VIX Fix, ATR-based) which synthesize a fear proxy
from the traded instrument's own price rather than referencing the real
VIX.

Signal logic
------------
- price_df is the TRADED instrument (e.g. SPY, QQQ, BTC/USDT); this
  strategy internally fetches ^VIX (equity only -- crypto has no VIX
  analog, tested as an explicit falsification check) via data/loaders.py
  and computes the CVR3 buy signal on VIX, then expresses a long position
  in price_df.
- VIX 10-day SMA; PPO-equivalent extension = 100 * (VIX_close - VIX_sma)
  / VIX_sma.
- Entry (long the traded instrument): VIX_low > VIX_sma AND extension >=
  entry_pct (default 10) AND VIX_close < VIX_open.
- Exit: VIX_close < previous day's VIX_sma (stop-loss per source), OR a
  max_hold_days time-stop (default 3, within source's suggested 2-4 day
  range).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_vix(index: pd.DatetimeIndex, asset_class: str) -> pd.DataFrame | None:
    """Fetch ^VIX OHLC over price_df's date range. Returns None for crypto
    (no VIX analog -- explicit falsification path)."""
    if asset_class == "crypto":
        return None
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = index.min()
    end = index.max() + timedelta(days=2)
    vix_df = load_equity("^VIX", start, end)
    vix_df = _prep(vix_df)
    return vix_df


def generate_signals(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    entry_pct: float = 10.0,
    max_hold_days: int = 3,
) -> pd.Series:
    df = _prep(price_df)
    vix_df = _load_vix(df.index, asset_class)

    position = pd.Series(0, index=df.index, dtype=int)
    if vix_df is None:
        # No VIX analog for crypto -- always flat (falsification check).
        return position

    vix_df = vix_df.reindex(df.index).ffill()
    vix_close = vix_df["close"]
    vix_open = vix_df["open"]
    vix_low = vix_df["low"]
    vix_sma = vix_close.rolling(10).mean()
    vix_sma_prev = vix_sma.shift(1)
    extension = 100.0 * (vix_close - vix_sma) / vix_sma

    in_position = False
    hold_days = 0

    for i in range(len(df.index)):
        vc = vix_close.iloc[i]
        vo = vix_open.iloc[i]
        vl = vix_low.iloc[i]
        vs = vix_sma.iloc[i]
        vs_prev = vix_sma_prev.iloc[i]
        ext = extension.iloc[i]

        if in_position:
            hold_days += 1
            stop_hit = (not pd.isna(vs_prev)) and vc < vs_prev
            if stop_hit or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
            else:
                position.iloc[i] = 1
        else:
            buy_signal = (
                not pd.isna(vs) and not pd.isna(ext)
                and vl > vs
                and ext >= entry_pct
                and vc < vo
            )
            if buy_signal:
                in_position = True
                hold_days = 1
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    entry_pct: float = 10.0,
    max_hold_days: int = 3,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        asset_class=asset_class,
        entry_pct=entry_pct,
        max_hold_days=max_hold_days,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
