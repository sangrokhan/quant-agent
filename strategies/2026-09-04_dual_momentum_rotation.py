"""Strategy: Dual Momentum (Gary Antonacci / GEM-style) two-asset rotation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-097):
Each month-end, compare the trailing 12-month (252 trading day) return of
the primary asset vs. a companion asset (relative momentum). Hold whichever
of the two has the higher trailing return for the next month, but ONLY if
that asset's own trailing 12-month return is positive (absolute momentum
gate) -- otherwise go to cash (flat) for that month. This differs from the
already-rejected single-asset TSMOM strategy (2026-09-03/-04 tsmom_12m,
rejected on Sharpe) by adding a RELATIVE-momentum asset-selection step on
top of the absolute-momentum gate, per Antonacci's actual GEM methodology
(rather than trading one asset unconditionally whenever its own absolute
momentum is positive).

Data note: this repo's data/loaders.py only exposes equity/crypto OHLCV (no
bond ETF like AGG, which the source's original GEM uses as the safe-haven
asset) -- cash (0% return, i.e. flat position) is used as the safe-haven
proxy instead of a bond ETF, an explicit, documented simplification.

Signal logic
------------
- primary_symbol's price_df is passed in (as required by the grid-test
  contract); companion_symbol's price_df is fetched internally via
  data/loaders.py (equity companion via load_equity, crypto companion via
  load_crypto) -- this mirrors the repo convention of fetching data only
  through data/loaders.py, just for a second symbol inside the strategy
  module rather than the grid harness.
- On each month-end trading day: compute trailing `lookback_days` (default
  252) simple return for both primary and companion.
- If primary's trailing return > companion's trailing return AND primary's
  trailing return > 0: hold primary (weight 1) for the following month.
- Elif companion's trailing return > primary's trailing return AND
  companion's trailing return > 0: hold companion, but since this
  strategy's generate_returns must return a return series ALIGNED TO THE
  PRIMARY asset's index/returns (the grid-test/validator contract expects a
  single return series representing "the strategy"), holding the companion
  contributes the companion's realized return for that month, not the
  primary's.
- Else (neither has positive absolute momentum): flat (cash, 0 return) for
  that month.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position,
        1 whenever ANY asset is held (primary or companion), 0 when flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, blending primary/companion/cash depending on the monthly
        selection)
"""

from __future__ import annotations

import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity, load_crypto  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_companion(companion_symbol: str, asset_class: str, start, end) -> pd.Series:
    if asset_class == "crypto":
        df = load_crypto(companion_symbol, start, end, interval="1d")
    else:
        df = load_equity(companion_symbol, start, end)
    df = _prep(df)
    return df["close"]


def _month_end_mask(index: pd.DatetimeIndex) -> pd.Series:
    ser = pd.Series(index, index=index)
    month = ser.dt.to_period("M") if hasattr(ser, "dt") else None
    # month-end = last trading day whose next day is a different month (or last row)
    periods = index.to_period("M")
    is_month_end = pd.Series(False, index=index)
    for i in range(len(index) - 1):
        if periods[i] != periods[i + 1]:
            is_month_end.iloc[i] = True
    if len(index) > 0:
        is_month_end.iloc[-1] = True
    return is_month_end


def _simulate(
    price_df: pd.DataFrame,
    companion_symbol: str = "SPY",
    asset_class: str = "equity",
    lookback_days: int = 252,
) -> pd.DataFrame:
    df = _prep(price_df)
    primary_close = df["close"]
    start, end = df.index.min(), df.index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None)
    companion_close = _load_companion(companion_symbol, asset_class, start, end)
    companion_close = companion_close.reindex(primary_close.index, method="ffill")

    primary_trail = primary_close.pct_change(lookback_days)
    companion_trail = companion_close.pct_change(lookback_days)

    is_month_end = _month_end_mask(primary_close.index)

    primary_daily_ret = primary_close.pct_change().fillna(0.0)
    companion_daily_ret = companion_close.pct_change().fillna(0.0)

    holding = pd.Series("cash", index=primary_close.index, dtype=object)
    current = "cash"
    for i, ts in enumerate(primary_close.index):
        if is_month_end.iloc[i] and pd.notna(primary_trail.iloc[i]) and pd.notna(companion_trail.iloc[i]):
            p_ret, c_ret = primary_trail.iloc[i], companion_trail.iloc[i]
            if p_ret > c_ret and p_ret > 0:
                current = "primary"
            elif c_ret > p_ret and c_ret > 0:
                current = "companion"
            else:
                current = "cash"
        holding.iloc[i] = current

    # shift holding by 1 day: decision made at month-end close, applied starting next day
    holding_applied = holding.shift(1).fillna("cash")

    strat_ret = pd.Series(0.0, index=primary_close.index)
    strat_ret[holding_applied == "primary"] = primary_daily_ret[holding_applied == "primary"]
    strat_ret[holding_applied == "companion"] = companion_daily_ret[holding_applied == "companion"]

    position = (holding_applied != "cash").astype(int)
    return pd.DataFrame({"position": position, "returns": strat_ret}, index=primary_close.index)


def generate_signals(
    price_df: pd.DataFrame,
    companion_symbol: str = "SPY",
    asset_class: str = "equity",
    lookback_days: int = 252,
) -> pd.Series:
    result = _simulate(price_df, companion_symbol, asset_class, lookback_days)
    return result["position"]


def generate_returns(
    price_df: pd.DataFrame,
    companion_symbol: str = "SPY",
    asset_class: str = "equity",
    lookback_days: int = 252,
) -> pd.Series:
    result = _simulate(price_df, companion_symbol, asset_class, lookback_days)
    return result["returns"]
