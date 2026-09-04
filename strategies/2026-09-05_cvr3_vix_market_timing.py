"""Strategy: CVR3 VIX Market Timing (Larry Connors & Dave Landry).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-021):
Per StockCharts ChartSchool's exact rule disclosure, the CVR3 strategy uses
the CBOE Volatility Index ($VIX) as a fear/complacency gauge to time
mean-reversion entries in the S&P 500 (or other equity/crypto index used
here as a proxy risk asset). Buy signal (all 3 VIX-only conditions must
align on the same day):

1. VIX daily LOW is above its own 10-day SMA (entire VIX bar above the
   average -- a sustained spike, not just an intraday wick).
2. VIX close is at least `vix_pct_above` (10% per source) above its own
   10-day SMA (PPO(1,10,1) >= 10 in the source's own framing).
3. VIX closes BELOW its own open that day (a "down" VIX bar -- fear is
   already starting to fade intraday, source's own reversal-timing
   refinement).

Exit: source suggests either (a) VIX crossing back below the *prior* day's
10-day SMA, or (b) a fixed 2-4 day hold -- implemented here as whichever
comes first, plus a max_hold_days safety backstop matching this repo's
convention.

Note: economically this is designed for SPY/S&P500 specifically (VIX is the
S&P options-implied-vol index); testing it here on QQQ as well (correlated
large-cap equity index) and on crypto (BTC/ETH, as a cross-asset "does a
traditional-equity fear spike also predict a crypto bounce" stress test,
per this repo's standard multi-asset-class grid convention) is a deliberate
generalization test, not a claim the mechanism applies economically to
crypto.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)

Note: `price_df` is the TRADABLE asset (SPY/QQQ/BTC-USDT/ETH-USDT); VIX data
is fetched internally via data/loaders.load_equity("^VIX", ...) aligned to
price_df's date range, since VIX itself isn't the position -- it's the
signal source.
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fetch_vix(index: pd.DatetimeIndex) -> pd.DataFrame:
    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    vix = load_equity("^VIX", start, end)
    return _prep(vix)


def generate_signals(
    price_df: pd.DataFrame,
    vix_pct_above: float = 0.10,
    min_hold_days: int = 2,
    max_hold_days: int = 4,
) -> pd.Series:
    """Return a {0,1} long/flat position series on the TRADABLE asset in
    price_df, driven by VIX-based CVR3 buy/exit signals."""
    df = _prep(price_df)
    close = df["close"]

    vix = _fetch_vix(df.index)
    vix_sma10 = vix["close"].rolling(10).mean()

    cond1 = vix["low"] > vix_sma10
    cond2 = vix["close"] >= vix_sma10 * (1.0 + vix_pct_above)
    cond3 = vix["close"] < vix["open"]
    vix_buy_signal = (cond1 & cond2 & cond3).fillna(False)

    # Align VIX signal to price_df's index (reindex + ffill for any minor
    # date mismatches, e.g. crypto trades on weekends but VIX doesn't).
    entry = vix_buy_signal.reindex(close.index, method="ffill").fillna(False)

    # Exit rule: VIX crosses back below the PRIOR day's 10-day SMA.
    prior_day_sma = vix_sma10.shift(1)
    vix_exit_signal = (vix["close"] < prior_day_sma).reindex(close.index, method="ffill").fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_ok = held >= min_hold_days
            if (exit_ok and bool(vix_exit_signal.iloc[i])) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
