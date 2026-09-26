"""Strategy: Rolling VWAP standard-deviation band mean reversion, entered only
on a reversal-candlestick + confirmed-reclaim signal (not a vol-regime gate).

Hypothesis (see knowledge_base/strategies_log.jsonl id filled in Step 9):
Source: https://algolabhk.com/en/blogs/vwap-mean-reversion-trading
(fetched via browser_exec; web_extract backend not configured for this
domain -- DDGS-only extract backend cannot fetch page content).

This is a direct, targeted revisit of the already-rejected
2026-09-04-052 (rolling VWAP +/- volume-weighted-sigma bands, gated by a
realized-vol regime filter). That entry's own `notes` field flagged the
likely failure cause: "mechanically implementing band-touch entries without
the source's own recommended confirmation filters (rejection candle, RSI
divergence, Value Area alignment) omits exactly the context the source says
separates a real setup from a losing fade." This strategy tests that
specific fix using algolabhk.com's own disclosed 3-condition entry rule
(distinct source, same band-touch-mean-reversion family, but the first one
in this repo's history to actually implement the candlestick-confirmation
condition instead of a volatility-regime proxy):

    Condition 1: low touches/breaks the VWAP - band_std*sigma band.
    Condition 2: that bar is itself a "reversal candle" -- a long lower
      wick relative to its own range (lower_wick / range >= wick_ratio_min),
      proxying the source's "long lower wick, shrinking volume on the down
      move" description.
    Condition 3: within `confirm_window` bars after the touch, close
      reclaims back above the lower band (source's "price closes back
      inside the band, confirming the signal is valid").

Entry: long at the close of the bar that satisfies Condition 3 (the
reclaim/confirmation bar), not the touch bar itself -- this is the key
structural difference from 2026-09-04-052, which entered immediately on
the raw band-touch with no candle/reclaim confirmation at all.

Exit: first target = rolling VWAP itself (source's stated first target),
OR a max_hold_days time-stop (this repo's standard guard against
indefinite holds; the source's own second target/breakeven-stop mechanics
require intraday partial-fill tracking this repo's daily-bar vectorbt
framework cannot represent).

Interface contract for validators (see validation/validators.py and
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _rolling_vwap_bands(df: pd.DataFrame, vwap_window: int, band_std: float):
    close = df["close"]
    volume = df["volume"].astype(float)

    pv = close * volume
    rolling_vol_sum = volume.rolling(vwap_window).sum()
    vwap = pv.rolling(vwap_window).sum() / rolling_vol_sum

    sq_dev_weighted = (volume * (close - vwap) ** 2).rolling(vwap_window).sum()
    sigma = (sq_dev_weighted / rolling_vol_sum) ** 0.5

    lower_band = vwap - band_std * sigma
    return vwap, lower_band


def generate_signals(
    price_df: pd.DataFrame,
    vwap_window: int = 20,
    band_std: float = 2.0,
    wick_ratio_min: float = 0.4,
    confirm_window: int = 3,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]

    vwap, lower_band = _rolling_vwap_bands(df, vwap_window, band_std)

    # Condition 1: touch/break of the lower band.
    touch = low <= lower_band

    # Condition 2: reversal candle -- lower wick is a large fraction of the
    # bar's own range (source: "long lower wick, shrinking volume on the
    # down move"; volume-shrink is not separately testable here without a
    # second free parameter, so the wick-ratio condition carries the
    # candle-shape signal alone).
    bar_range = (high - low).replace(0.0, pd.NA)
    lower_wick = pd.concat([open_, close], axis=1).min(axis=1) - low
    wick_ratio = (lower_wick / bar_range).fillna(0.0)
    reversal_candle = wick_ratio >= wick_ratio_min

    touch_and_candle = touch & reversal_candle

    position = pd.Series(0, index=close.index, dtype=int)
    n = len(close)
    i = 0
    pending_touch_idx = None
    in_position = False
    entry_idx = 0

    while i < n:
        if in_position:
            held = i - entry_idx
            exit_target = bool(close.iloc[i] >= vwap.iloc[i]) if pd.notna(vwap.iloc[i]) else False
            if exit_target or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
            i += 1
            continue

        if pending_touch_idx is not None:
            # Condition 3: within confirm_window bars, close reclaims above
            # the lower band (using the band value as of the touch bar as
            # the reclaim threshold -- source's "closes back inside the
            # band").
            bars_since = i - pending_touch_idx
            if bars_since > confirm_window:
                pending_touch_idx = None
            else:
                threshold = lower_band.iloc[pending_touch_idx]
                if pd.notna(threshold) and pd.notna(close.iloc[i]) and close.iloc[i] > threshold:
                    in_position = True
                    entry_idx = i
                    position.iloc[i] = 1
                    pending_touch_idx = None
                    i += 1
                    continue

        if pending_touch_idx is None and bool(touch_and_candle.iloc[i]) if pd.notna(touch_and_candle.iloc[i]) else False:
            pending_touch_idx = i

        position.iloc[i] = 0
        i += 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
