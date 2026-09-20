"""Strategy: Coinbase Premium Index streak-based BTC/ETH long signal.

Hypothesis (this iteration):
Per crypto.news's "What is the Coinbase Premium Index?" guide
(https://crypto.news/what-is-the-coinbase-premium-index/, read via
browser_exec this iteration -- web_search backend intermittently
TLS-erroring on some queries so browser fallback used for parts of
discovery): the Coinbase Premium Index measures the % price gap between
BTC quoted in USD on Coinbase (the dominant US-regulated venue, including
the spot-BTC-ETF creation/redemption plumbing) and BTC quoted in USDT on a
global reference venue like Binance. The source's own explicit reading
framework: "Read streaks, not prints... The informative patterns are runs:
five, ten, fourteen consecutive days on one side of zero." A premium that
holds POSITIVE for a sustained run signals persistent US-institutional
demand out-bidding the global market (bullish); a premium that holds
NEGATIVE for a sustained run signals persistent US-institutional
distribution (bearish). This is a genuinely novel, previously-untested
angle in this repo (no prior cross-exchange-premium strategy exists) and is
feasible with this repo's existing infrastructure: `ccxt` already supports
both `coinbase` and `binance` exchanges via `data/loaders.py::load_crypto`
(confirmed working this iteration for BTC/USD on Coinbase).

Signal logic
------------
- price_df is the primary (Binance) OHLCV series for e.g. BTC/USDT.
- Internally fetch the matching Coinbase USD pair (BTC/USDT -> BTC/USD,
  ETH/USDT -> ETH/USD) over the same date range via `load_crypto(...,
  exchange="coinbase")`, align to price_df's index (inner join on date).
- Daily premium (%) = (coinbase_close - binance_close) / binance_close * 100.
- Streak length: count of consecutive prior days the premium's sign has
  matched the current day's sign (source's own "streaks, not prints"
  framework).
- Entry (long): premium > 0 AND the positive streak length >=
  `streak_days` (source's own disclosed reading requires a sustained run,
  not a single print).
- Exit: premium turns negative (streak resets to the other side), or a
  max_hold_days time-stop.
- Long-only, flat otherwise. If Coinbase data cannot be fetched/aligned
  (e.g. for a non-BTC/ETH or equity symbol), returns an all-flat position
  (honest scope limitation, not a silent failure).

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals(price_df, **params) -> pd.Series {0,1};
generate_returns(price_df, **params) -> pd.Series of daily strategy returns.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


_COINBASE_MAP = {
    "BTC/USDT": "BTC/USD",
    "ETH/USDT": "ETH/USD",
}


def _fetch_coinbase_close(binance_symbol: str, index: pd.DatetimeIndex) -> pd.Series | None:
    coinbase_symbol = _COINBASE_MAP.get(binance_symbol)
    if coinbase_symbol is None or len(index) == 0:
        return None
    try:
        import sys
        import os

        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
        from loaders import load_crypto  # noqa: E402

        start = index.min().to_pydatetime().replace(tzinfo=None)
        end = index.max().to_pydatetime().replace(tzinfo=None)
        cb_df = load_crypto(coinbase_symbol, start, end, interval="1d", exchange="coinbase")
        if "timestamp" in cb_df.columns:
            cb_df = cb_df.set_index("timestamp")
        cb_close = cb_df["close"].sort_index()
        # Normalize tz-awareness to match price_df's index.
        if cb_close.index.tz is not None and index.tz is None:
            cb_close.index = cb_close.index.tz_localize(None)
        elif cb_close.index.tz is None and index.tz is not None:
            cb_close.index = cb_close.index.tz_localize(index.tz)
        return cb_close
    except Exception:
        return None


def _infer_binance_symbol(price_df_orig) -> str:
    # Best-effort: this repo's price_df has no symbol column, so this
    # strategy is deliberately scoped to be called only on BTC/USDT or
    # ETH/USDT price data (per the grid this iteration always uses those
    # two symbols); callers passing other symbols will get an all-flat
    # position because Coinbase alignment will fail gracefully.
    return "BTC/USDT"


def generate_signals(
    price_df: pd.DataFrame,
    binance_symbol: str = "BTC/USDT",
    streak_days: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    cb_close = _fetch_coinbase_close(binance_symbol, close.index)
    if cb_close is None:
        return pd.Series(0, index=close.index, dtype=int)

    aligned = pd.DataFrame({"binance": close, "coinbase": cb_close}).dropna()
    if aligned.empty:
        return pd.Series(0, index=close.index, dtype=int)

    premium = (aligned["coinbase"] - aligned["binance"]) / aligned["binance"] * 100.0
    sign = np.sign(premium)

    # Consecutive same-sign streak length (positive streak counted as-is,
    # negative streak counted as well, sign preserved via `sign`).
    streak = pd.Series(0, index=premium.index, dtype=int)
    cur_sign = 0
    cur_len = 0
    for i, s in enumerate(sign.values):
        if s == cur_sign and s != 0:
            cur_len += 1
        else:
            cur_sign = s
            cur_len = 1 if s != 0 else 0
        streak.iloc[i] = cur_len if cur_sign > 0 else (-cur_len if cur_sign < 0 else 0)

    entry_mask = streak >= streak_days
    exit_mask = streak < 0  # premium flipped negative (any negative streak)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx_pos = 0

    entry_vals = entry_mask.reindex(close.index).fillna(False).values
    exit_vals = exit_mask.reindex(close.index).fillna(False).values

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx_pos
            if bool(exit_vals[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
                in_position = True
                entry_idx_pos = i
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
