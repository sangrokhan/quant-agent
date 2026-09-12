"""Strategy: VIX 20-day-high breakout + VIX RSI(5) stretch confirmation ->
long the underlying equity index, exit on close > yesterday's high.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-13-019):
Per https://www.quantifiedstrategies.com/vix-trading-strategy/ (read via
browser_exec fallback this iteration, after web_search's DDGS backend
returned no usable results for the VIX-trend-following query), the source's
own disclosed rule: "go long the S&P 500 when the VIX breaks out on a new
20-day high and at the same time has a five-day RSI value of at least 65,"
exiting "when the close is higher than yesterday's high." The source
reports this as one of several VIX mean-reversion setups, with the RSI
condition included specifically "to make sure the VIX is somewhat
'stretched' when it breaks out" (avoiding weak/marginal new highs). This is
distinct from every other VIX-family strategy already tested in this repo
(VIX Bollinger-Band breakout 2026-09-04-103, VIX/VIX3M term structure
2026-09-04-157, CVR3 2026-09-05-021/2026-09-08-080, Connors VIX-RSI applied
TO price 2026-09-05-052/2026-09-11-018, Williams VIX Fix 2026-09-06-115/
2026-09-10-099, VVIX level/ratio 2026-09-10-022/042) because the entry here
requires a genuine VIX PRICE breakout (new N-day high in the VIX itself)
combined with an RSI-on-the-VIX confirmation, not a VIX Bollinger Band
touch, a VIX/SMA ratio condition, or an RSI applied to the underlying's own
price.

Signal logic
------------
- VIX new high: today's ^VIX close is the highest close over the trailing
  vix_high_window (default 20) trading days.
- VIX RSI stretch: a standard Wilder RSI(vix_rsi_window) computed on ^VIX
  closes is >= vix_rsi_threshold (default 65) on the same day.
- Entry (long the underlying, price_df is expected to be SPY/QQQ/BTC/ETH):
  VIX new-high AND VIX RSI stretch both true on the same day.
- Exit: close > yesterday's high (source's own exit rule) OR a
  max_hold_days time-stop backstop (the source's exit could otherwise hold
  indefinitely if the underlying never makes a higher-high day).
- Flat otherwise. Long-only per SAFETY.md.

Interface contract for validators (see validation/validators.py) and the
grid tester (see validation/grid_test.py): both generate_signals and
generate_returns accept price_df (the underlying instrument) plus the
strategy's tunable parameters as keyword arguments; ^VIX data is fetched
internally via data/loaders.py.load_equity (same pattern as this repo's
other VIX-family strategies, e.g. 2026-09-08_cvr3_vix_market_timing.py).
Crypto (BTC/ETH) has no VIX analog, so this strategy returns an all-flat
(zero) position series when applied to a non-equity asset without a VIX
proxy -- included in the grid purely as a falsification check, per this
repo's established convention (e.g. 2026-09-08-080's own crypto row).
"""

from __future__ import annotations

import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wilder_rsi(series: pd.Series, window: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def _load_vix_close(start, end) -> pd.Series:
    df = load_equity("^VIX", start, end)
    df = _prep(df)
    return df["close"]


def generate_signals(
    price_df: pd.DataFrame,
    vix_high_window: int = 20,
    vix_rsi_window: int = 5,
    vix_rsi_threshold: float = 65.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series for the underlying."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close

    start = df.index.min()
    end = df.index.max()
    try:
        vix_close = _load_vix_close(start, end)
    except Exception:
        # No VIX analog available (e.g. crypto asset) -- all-flat falsification check.
        return pd.Series(0, index=close.index, dtype=int)

    vix_close = vix_close.reindex(close.index).ffill()

    vix_rolling_high = vix_close.rolling(vix_high_window).max()
    vix_new_high = vix_close >= vix_rolling_high

    vix_rsi = _wilder_rsi(vix_close, vix_rsi_window)
    vix_stretched = vix_rsi >= vix_rsi_threshold

    entry = (vix_new_high & vix_stretched).fillna(False)

    prior_high = high.shift(1)
    exit_signal = close > prior_high

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    entry_vals = entry.values
    exit_vals = exit_signal.fillna(False).values

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_vals[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    vix_high_window: int = 20,
    vix_rsi_window: int = 5,
    vix_rsi_threshold: float = 65.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        vix_high_window=vix_high_window,
        vix_rsi_window=vix_rsi_window,
        vix_rsi_threshold=vix_rsi_threshold,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = daily_ret * position.shift(1).fillna(0)
    return strat_returns
