"""Strategy: Bollinger-Band-Width (BBW) percentile squeeze -> volume-confirmed
directional breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-036):
Per VolatilityBox's "Bollinger Bands and Volatility: How to Trade Squeezes
and Breakouts" (https://volatilitybox.com/research/bollinger-bands-volatility/,
read via browser_exec since web_extract's ddgs backend cannot extract page
content): Bollinger Band Width (BBW = (upper-lower)/middle*100) compresses
before a directional breakout. When BBW drops below its own trailing
`bbw_pctile_window`-day low (approximated here as "at/near its rolling
percentile minimum", implemented as BBW <= its `bbw_pctile` percentile over
the trailing window), a squeeze is in effect. When a bar then closes outside
the Bollinger Band (above upper = long breakout signal) WITH volume at least
`volume_mult`x the `volume_window`-day average volume, that's a
high-conviction directional entry -- the source explicitly warns that
breakouts on average/below-average volume are prone to failure, hence the
mandatory volume filter (not present in the earlier, already-tested/rejected
plain BB mean-reversion strategies in this repo, e.g. 2026-09-03-001, which
fade INTO the bands rather than trade the breakout OUT of them -- this is
the opposite directional bet, trend-following not mean-reverting). Distinct
also from the just-rejected VWAP-deviation strategy (2026-09-27-035, also a
band/SD construction but that one deliberately fades extensions rather than
trading breakouts).

Signal logic
------------
- 20-day Bollinger Bands (SMA + bb_std * rolling std).
- BBW = (upper - lower) / middle * 100.
- Squeeze condition: BBW <= its own rolling `bbw_pctile`-th percentile over
  the trailing `bbw_window` days (a narrow-bands regime).
- Entry (long): squeeze was active within the last `lookback_bars` bars AND
  close > upper band this bar AND volume >= volume_mult * rolling
  `volume_window`-day average volume.
- Stop: lower band value AT the squeeze bar (approximated as the band value
  `lookback_bars` before entry) -- exit if close falls back below that
  level.
- Exit (profit-taking): close falls back below the 20-day SMA (middle
  band) -- trailing-stop-to-middle-band per the source's guidance -- OR
  after max_hold_days elapsed.
- Long-only, matching this repo's other accepted strategies' convention.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    bbw_window: int = 120,
    bbw_pctile: float = 10.0,
    lookback_bars: int = 5,
    volume_window: int = 20,
    volume_mult: float = 1.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)
    volume = volume.replace(0, float("nan")).ffill().fillna(1.0)

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    upper = sma + bb_std * std
    lower = sma - bb_std * std
    bbw = (upper - lower) / sma.replace(0, float("nan")) * 100.0

    bbw_threshold = bbw.rolling(bbw_window, min_periods=bb_window).quantile(bbw_pctile / 100.0)
    squeeze = bbw <= bbw_threshold
    squeeze_recent = squeeze.rolling(lookback_bars, min_periods=1).max().astype(bool)

    avg_volume = volume.rolling(volume_window).mean()
    volume_confirmed = volume >= (volume_mult * avg_volume)

    breakout_entry = (close > upper) & squeeze_recent.shift(1).fillna(False) & volume_confirmed

    exit_below_mid = close < sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = None
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if (stop_level is not None and close.iloc[i] < stop_level) or bool(
                exit_below_mid.iloc[i]
            ) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                stop_level = None
                continue
            position.iloc[i] = 1
        else:
            if bool(breakout_entry.iloc[i]):
                in_position = True
                entry_idx = i
                stop_idx = max(0, i - lookback_bars)
                stop_level = lower.iloc[stop_idx]
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    bbw_window: int = 120,
    bbw_pctile: float = 10.0,
    lookback_bars: int = 5,
    volume_window: int = 20,
    volume_mult: float = 1.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (position-weighted, no costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        bb_window=bb_window,
        bb_std=bb_std,
        bbw_window=bbw_window,
        bbw_pctile=bbw_pctile,
        lookback_bars=lookback_bars,
        volume_window=volume_window,
        volume_mult=volume_mult,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
