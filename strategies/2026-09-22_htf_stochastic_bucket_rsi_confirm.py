"""Strategy: Higher-Timeframe Stochastic Bucket + same-timeframe RSI confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-051):
Per LuxAlgo's "Higher Timeframe Stochastic Buckets" indicator
(https://www.luxalgo.com/library/indicator/higher-timeframe-stochastic-buckets/,
published Aug 17 2026, read via browser_exec this iteration -- web_search
DDGS backend TLS-errored on all queries), when a HIGHER timeframe Stochastic
oscillator enters an oversold zone, it marks a "bucket" of macro
overextension; the source's own disclosed rule set says to treat that as a
"strong structural boundary" and use the CURRENT-timeframe RSI extreme as
the "localized trigger, suggesting price is beginning to turn in alignment
with the higher timeframe extremity."

Adapted here to a daily-bar-only, single-symbol implementation (this repo's
architectural constraint -- no true multi-timeframe intrabar data): the
"higher timeframe" is approximated by resampling daily OHLCV to WEEKLY bars
and computing a standard %K/%D Stochastic on that weekly series, forward-
filled back onto the daily index (the LuxAlgo indicator explicitly overlays
higher-timeframe extremes onto the current/lower chart this way). Long
entry: weekly Stochastic %K (and %D, per the source's "Require %D
Confirmation" option) is below oversold_htf (macro "bucket" active) AND the
daily RSI crosses up from below oversold_ltf (the "localized trigger").
Exit: the weekly bucket breaks (weekly %K rises back above oversold_htf --
mirrors the source's "Hide Broken Zones... once price closes beyond the
extreme level") OR daily RSI crosses back above 50, OR a max_hold_days
time-stop.

First strategy in this repo using a resampled higher-timeframe oscillator as
a regime/bucket gate combined with a same-timeframe oscillator trigger --
distinct from all prior single-timeframe Stochastic/RSI combos (Stochastic
RSI, MESA/Ehlers Stochastic, RSI-2 Connors, RSI divergence family) since
none of those cross a genuinely different (weekly-vs-daily) resampled
timeframe.

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


def _stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_length: int, k_smooth: int, d_smooth: int):
    lowest_low = low.rolling(k_length).min()
    highest_high = high.rolling(k_length).max()
    raw_k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, pd.NA)
    k = raw_k.rolling(k_smooth).mean()
    d = k.rolling(d_smooth).mean()
    return k, d


def _rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    htf_k_length: int = 14,
    htf_k_smooth: int = 3,
    htf_d_smooth: int = 3,
    oversold_htf: float = 20.0,
    require_d_confirmation: bool = True,
    rsi_length: int = 14,
    oversold_ltf: float = 30.0,
    exit_rsi: float = 50.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    # Higher timeframe (weekly) Stochastic, forward-filled onto daily index.
    weekly = df.resample("W").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    wk_k, wk_d = _stochastic(weekly["high"], weekly["low"], weekly["close"], htf_k_length, htf_k_smooth, htf_d_smooth)
    wk_k_daily = wk_k.reindex(close.index, method="ffill")
    wk_d_daily = wk_d.reindex(close.index, method="ffill")

    if require_d_confirmation:
        htf_bucket_active = (wk_k_daily <= oversold_htf) & (wk_d_daily <= oversold_htf)
    else:
        htf_bucket_active = wk_k_daily <= oversold_htf
    htf_bucket_active = htf_bucket_active.fillna(False)

    rsi = _rsi(close, rsi_length)
    rsi_prev = rsi.shift(1)
    rsi_trigger_up = (rsi_prev < oversold_ltf) & (rsi >= oversold_ltf)

    entry = htf_bucket_active & rsi_trigger_up
    exit_bucket_broken = wk_k_daily > oversold_htf
    exit_rsi_reverted = rsi > exit_rsi

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_bucket_broken.iloc[i]) or bool(exit_rsi_reverted.iloc[i]) or held >= max_hold_days:
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
