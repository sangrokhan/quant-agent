"""Strategy: Katsanos capitulation-bottom (VIX spike + dual-stochastic stack).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-162):
Markos Katsanos' article (TASC Jul 2021, "Buy & Hold, Or Buy & Sell?",
source: Traders.com Jul 2021 Traders' Tips, TradeStation EasyLanguage code
read this iteration) is a weekly SPY+VIX strategy that tries to time
capitulation bottoms and euphoria tops. This adaptation focuses on the
BUY ("B2") capitulation-bottom leg, rescaled to daily bars: a genuine
market bottom is characterized by (1) a sharp recent bounce off the lows
(UP), (2) VIX having spiked and then crashed back down from its own
15-period high (fear peaking and subsiding -- VIXDN), (3) a deep pullback
from the recent 100-day high (CCH), and (4) BOTH a fast (14-period) and
slow (40-period) stochastic %K being simultaneously oversold with the fast
one crossing above the slow one (a "bullish stack" -- momentum turning up
across two different lookback horizons simultaneously, not just one). This
specific combination (VIX-capitulation-spike + deep-pullback + dual-length
stochastic-stack confirmation) is novel in this repo -- distinct from every
prior single-stochastic or single-VIX-threshold strategy already tested.

Formula (per source, daily-bar adaptation; original is a weekly chart)
------------------------------------------------------------------------
- UP = (Highest(Close, up_window) / Lowest(Close, up_window*2) - 1) * 100
- VIXDN = (VIXClose / Highest(VIXClose, vix_window).shift(1) - 1) * 100
- CCH = (Lowest(Close, cch_short) / Highest(Close, cch_long) - 1) * 100
- SlowK(length, smooth) = %K stochastic with `smooth`-period SMA smoothing
  of the raw %K.
- B2 (buy) = UP > up_threshold AND VIXDN < vix_dn_min AND CCH < cch_threshold
  AND SlowK(fast_len) < oversold AND SlowK(slow_len) < oversold AND
  SlowK(fast_len) >= SlowK(slow_len)

Signal logic (long-only; original's sell/short leg for the euphoria-top
mirror not implemented -- kept as a simple time-stop exit for this
adaptation)
------------------------------------------------------------------------
- Entry (long): B2 condition true.
- Exit: after `max_hold_days`, OR close falls below its own `exit_sma`-day
  SMA (basic trend-loss stop, since the source's own SellSignal mirror is
  out of scope for this long-only adaptation).
- No short leg.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _naive(ts):
    py = ts.to_pydatetime()
    return py.replace(tzinfo=None) if py.tzinfo is not None else py


def _load_vix_close(index: pd.DatetimeIndex, vix_symbol: str = "^VIX") -> pd.Series:
    from loaders import load_equity  # data/loaders.py, already on sys.path via strategies/ caller convention

    start = _naive(index.min()) if len(index) else datetime(2015, 1, 1)
    end = _naive(index.max()) if len(index) else datetime.utcnow()
    vix_df = _prep(load_equity(vix_symbol, start, end))
    vix_close = vix_df["close"].reindex(index.union(vix_df.index)).sort_index().ffill()
    return vix_close.reindex(index)


def _slow_k(close: pd.Series, high: pd.Series, low: pd.Series, length: int, smooth: int) -> pd.Series:
    lowest = low.rolling(length).min()
    highest = high.rolling(length).max()
    rng = (highest - lowest).replace(0, pd.NA)
    raw_k = (close - lowest) / rng * 100
    return raw_k.rolling(smooth).mean()


def generate_signals(
    price_df: pd.DataFrame,
    up_window: int = 10,
    vix_window: int = 30,
    vix_dn_min: float = -20.0,
    cch_short: int = 20,
    cch_long: int = 150,
    cch_threshold: float = -15.0,
    up_threshold: float = 6.0,
    fast_len: int = 20,
    slow_len: int = 60,
    smooth: int = 5,
    oversold: float = 25.0,
    exit_sma: int = 20,
    max_hold_days: int = 40,
    vix_symbol: str = "^VIX",
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    vix_close = _load_vix_close(df.index, vix_symbol=vix_symbol)

    up = (close.rolling(up_window).max() / close.rolling(up_window * 2).min() - 1) * 100
    vix_dn = (vix_close / vix_close.rolling(vix_window).max().shift(1) - 1) * 100
    cch = (close.rolling(cch_short).min() / close.rolling(cch_long).max() - 1) * 100

    slow_k_fast = _slow_k(close, high, low, fast_len, smooth)
    slow_k_slow = _slow_k(close, high, low, slow_len, smooth)

    b2 = (
        (up > up_threshold)
        & (vix_dn < vix_dn_min)
        & (cch < cch_threshold)
        & (slow_k_fast < oversold)
        & (slow_k_slow < oversold)
        & (slow_k_fast >= slow_k_slow)
    )

    sma_exit = close.rolling(exit_sma).mean()
    exit_trend_loss = close < sma_exit

    warmup = max(up_window * 2, vix_window, cch_long, slow_len, exit_sma) + smooth

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if i < warmup:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(exit_trend_loss.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(b2.iloc[i]):
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
