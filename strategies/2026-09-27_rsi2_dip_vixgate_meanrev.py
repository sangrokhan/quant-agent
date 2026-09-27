"""Strategy: Two-Day RSI(2) Dip-Buy Mean Reversion, VIX-Gated (QuanterLab).

Hypothesis (see knowledge_base/strategies_log.jsonl entry for this
iteration's id): Per QuanterLab's "Navigating Mean Reversion: Breaking
Down the Base Mechanism" (Serhat Girgin,
https://quanterlab.com/research/navigating-mean-reversion-breaking-down-the-base-mechanism,
read via browser_exec this iteration -- web_search's DDGS backend
returned "No results found" for the initial query, resolved via
quantocracy.com's blog-mashup listing then followed to the source), the
"plainest" mean-reversion rule tested across all S&P 500 members for 20
years: "A dip is a day on which the two-day RSI... falls below 10 while
the close is still above its 200-day average... The position is sold
when the close is back above its 5-day average." The source's own
headline cost-survival finding: taking every dip trades ~2,480x/year and
barely survives costs (pooled Sharpe 0.30 at 0.1% cost/side), but gating
entries to dips that occur after a VIX close >= 20 the prior session cuts
trade count to ~740/year and keeps MORE return after costs (pooled Sharpe
0.47) -- "most of the difference made in 2020 to 2022" (i.e. the edge
concentrates in genuinely stressed regimes, not quiet dips).

This repo has RSI(2) mean-reversion entries and VIX-gated strategies
separately, but not this exact combination: RSI(2)<10 (not the more
common <5 threshold used elsewhere in this repo's Connors/Alvarez-style
strategies) + close>SMA(200) trend filter + exit on close>SMA(5) (a
short-MA recross exit, distinct from this repo's more common
fixed-RSI-recovery-level exits) + an optional VIX>=vix_threshold prior-day
gate replicating the source's own disclosed cost-survival rescue.

Signal logic
------------
- RSI(2) of the primary asset's close (Wilder-style with EWMA seed).
- SMA(200) trend filter on the primary asset's close.
- SMA(5) short-term average, used as the exit trigger.
- Entry (long) at close when: RSI(2) < rsi_entry AND close > SMA(200) AND
  (if use_vix_gate) VIX close on the PRIOR bar >= vix_threshold.
- Exit (flat) at close when: close > SMA(5).
- max_hold_days safety valve (this repo's convention; the source's own
  headline stats imply exits usually happen quickly but no explicit cap
  is disclosed).

VIX is fetched internally via the same equity loader (ticker "^VIX"),
mirroring this repo's established pattern for VIX-gated strategies (e.g.
2026-09-05-052).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position).
"""

from __future__ import annotations

from typing import Callable, Optional

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _get_vix_close(
    price_df: pd.DataFrame,
    vix_loader: Optional[Callable] = None,
) -> Optional[pd.Series]:
    if vix_loader is None:
        return None
    df = _prep(price_df)
    start = df.index.min()
    end = df.index.max()
    start_dt = start.to_pydatetime() if hasattr(start, "to_pydatetime") else start
    end_dt = end.to_pydatetime() if hasattr(end, "to_pydatetime") else end
    try:
        vix_df = vix_loader("^VIX", start_dt, end_dt, interval="1d")
    except TypeError:
        vix_df = vix_loader("^VIX", start_dt, end_dt)
    vix_df = _prep(vix_df)
    return vix_df["close"].reindex(df.index).ffill()


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 2,
    rsi_entry: float = 10.0,
    trend_window: int = 200,
    exit_sma_window: int = 5,
    max_hold_days: int = 15,
    use_vix_gate: bool = False,
    vix_threshold: float = 20.0,
    vix_loader: Optional[Callable] = None,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi2 = _rsi(close, rsi_period)
    sma_trend = close.rolling(trend_window).mean()
    sma_exit = close.rolling(exit_sma_window).mean()

    entry = (rsi2 < rsi_entry) & (close > sma_trend)

    if use_vix_gate:
        vix_close = _get_vix_close(price_df, vix_loader)
        if vix_close is not None:
            vix_prior_day_elevated = vix_close.shift(1) >= vix_threshold
            entry = entry & vix_prior_day_elevated.fillna(False)

    exit_signal = close > sma_exit

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) if pd.notna(entry.iloc[i]) else False:
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
    strategy_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strategy_ret
