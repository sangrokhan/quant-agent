"""Strategy: Donchian breakout gated by a VIX "goldilocks zone" regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-16-167):
Per https://volatilitybox.com/research/opening-range-volatility-breakout/
(read via browser_exec fallback this iteration -- web_extract's DuckDuckGo
backend is search-only and cannot fetch page content), the article's own
disclosed backtest table states that opening-range-breakout day-trading
setups achieve their HIGHEST win rate (58-62%) specifically when VIX is in
the 16-25 "goldilocks" band -- neither too calm (VIX<16, insufficient range
expansion/opening range too narrow to trade profitably net of costs) nor
too chaotic (VIX>25, false-breakout rate spikes as the U-shaped intraday
vol pattern gets swamped by macro-driven whipsaws). This is an intraday
mechanism description; this repo only has daily bars, so we adapt it as a
DAILY regime filter: trade a classic Donchian channel breakout only on days
where VIX's own close falls inside [vix_low, vix_high], flat otherwise --
testing whether the "sweet spot volatility, not too calm not too chaotic"
finding generalizes from the intraday ORB mechanism to a daily swing
breakout regime filter.

This is distinct from every prior VIX-gated strategy in this repo:
- 2026-09-04-103 (VIX Bollinger Band breakout -> SPY mean-reversion bounce)
- 2026-09-05-021 (CVR3: VIX spike + reversal timing, mean-reversion entry)
- 2026-09-05-043 (MOVE index panic-spike regime filter)
- 2026-09-05-044 (VRP regime filter)
- 2026-09-05-089/2026-09-06-115 (VIX-adjacent oscillator spike bounces)
- 2026-09-13-019 (VIX N-day-high breakout + RSI stretch -> index long)
None of these use a two-sided BAND regime filter (calm floor AND chaos
ceiling) gating a price BREAKOUT (not mean reversion) on the underlying
asset itself. This is a genuinely new construction: trend-following signal
(Donchian breakout), regime-gated by VIX being in a moderate zone rather
than by a VIX spike/dip event.

Signal logic
------------
- Compute a Donchian channel on the tradable asset: rolling `entry_window`
  high/low.
- Entry (long): close breaks above its own rolling `entry_window`-day high
  AND VIX close (as of that bar) is within [vix_low, vix_high] (the
  goldilocks band).
- Exit: close breaks below its own rolling `exit_window`-day low
  (asymmetric Donchian exit, Turtle-style) OR VIX exits the goldilocks band
  (regime flip -- either too calm or too chaotic) OR a max_hold_days
  time-stop backstop.
- Flat otherwise.

For crypto (no VIX), we substitute a realized-volatility-percentile proxy
band on the asset's own 20d annualized realized vol (percentile 30-70 of
its trailing 252d distribution) as the closest same-asset analogue of
"moderate, not extreme, volatility regime" -- explicitly a generalization
test of the economic mechanism (does trading Donchian breakouts only in a
moderate-vol regime help), not a literal transplant of the VIX-specific
rule.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)
"""

from __future__ import annotations

import os
import sys
from datetime import timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fetch_vix(index: pd.DatetimeIndex) -> pd.Series:
    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    vix = load_equity("^VIX", start, end)
    vix = _prep(vix)
    return vix["close"]


def _goldilocks_mask(
    df: pd.DataFrame,
    is_crypto: bool,
    vix_low: float,
    vix_high: float,
    rv_low_pct: float,
    rv_high_pct: float,
    rv_window: int,
    rv_lookback: int,
) -> pd.Series:
    if not is_crypto:
        vix_close = _fetch_vix(df.index)
        vix_close = vix_close.reindex(df.index).ffill()
        return (vix_close >= vix_low) & (vix_close <= vix_high)

    log_ret = np.log(df["close"]).diff()
    rv = log_ret.rolling(rv_window).std() * np.sqrt(252)
    rv_pct_rank = rv.rolling(rv_lookback, min_periods=max(30, rv_window)).apply(
        lambda x: (x.rank(pct=True).iloc[-1]) if len(x) > 0 else np.nan, raw=False
    )
    return (rv_pct_rank >= rv_low_pct) & (rv_pct_rank <= rv_high_pct)


def generate_signals(
    price_df: pd.DataFrame,
    entry_window: int = 20,
    exit_window: int = 10,
    vix_low: float = 16.0,
    vix_high: float = 25.0,
    rv_low_pct: float = 0.30,
    rv_high_pct: float = 0.70,
    rv_window: int = 20,
    rv_lookback: int = 252,
    max_hold_days: int = 20,
    is_crypto: bool = False,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    rolling_high = close.rolling(entry_window).max()
    rolling_low = close.rolling(exit_window).min()

    entry_breakout = close > rolling_high.shift(1)
    exit_breakdown = close < rolling_low.shift(1)

    regime_ok = _goldilocks_mask(
        df, is_crypto, vix_low, vix_high, rv_low_pct, rv_high_pct, rv_window, rv_lookback
    ).fillna(False)

    entry_signal = (entry_breakout & regime_ok).fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(df)):
        if in_position:
            held = i - entry_idx
            if exit_breakdown.iloc[i] or (not regime_ok.iloc[i]) or held >= max_hold_days:
                in_position = False
            else:
                position.iloc[i] = 1
        else:
            if entry_signal.iloc[i]:
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    position = generate_signals(price_df, **params)
    position = position.reindex(df.index).fillna(0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
