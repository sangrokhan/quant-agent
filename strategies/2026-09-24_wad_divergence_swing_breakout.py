"""Strategy: Williams Accumulation/Distribution (WAD) bullish-divergence
swing-breakout with ATR stop / 2R target.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per cTrader's Williams Accumulation Distribution documentation
(https://help.ctrader.com/indicators/built-in/other/williams-accumulation-distribution)
and Google AI-overview synthesis of WAD trading-strategy sources: WAD
(Larry Williams) is the cumulative sum of a per-bar accumulation/
distribution value that uses "true range" reference points (a prior
close, not just that bar's own high/low) to gauge buying vs selling
pressure -- distinct from OBV (which uses raw volume x price-direction
sign, already tested in this repo's 2026-09-23-030 OBV divergence entry)
because WAD is purely price-derived (no volume term at all) and uses each
bar's relation to the PRIOR close as its true-range reference, similar in
spirit to Wilder's true-range construction but applied to an
accumulation/distribution running sum rather than a volatility measure.
The primary disclosed strategy: bullish divergence (price makes a lower
low, WAD makes a higher low at the same two swing points -- hidden buying
pressure despite price weakness) triggers a long entry on a confirmed
breakout above the swing high between the two divergence lows, with an
ATR-based stop and a minimum 2R reward:risk target. First WAD entry in
this repo (0 prior KB hits) -- reuses this repo's established OBV-
divergence swing-breakout construction (2026-09-23-030) applied to WAD for
the first time, since WAD's price-only (no-volume) construction is a
genuinely distinct signal source even though the divergence detection
mechanics are structurally similar.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wad(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    true_low = pd.concat([low, prev_close], axis=1).min(axis=1)
    true_high = pd.concat([high, prev_close], axis=1).max(axis=1)

    up_day = close > prev_close
    down_day = close < prev_close

    ad = pd.Series(0.0, index=close.index)
    ad[up_day] = (close - true_low)[up_day]
    ad[down_day] = (close - true_high)[down_day]
    ad = ad.fillna(0.0)
    return ad.cumsum()


def _atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def _swing_lows(close: pd.Series, window: int) -> pd.Series:
    """Boolean mask: True where close[i] is the min over [i-window, i+window]."""
    roll_min = close.rolling(window * 2 + 1, center=True).min()
    return close == roll_min


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    lookback_bars: int = 30,
    atr_window: int = 14,
    reward_risk: float = 2.0,
    max_hold_bars: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    wad = _wad(df)
    atr = _atr(df, atr_window)
    is_swing_low = _swing_lows(close, swing_window)

    swing_idx = [i for i, v in enumerate(is_swing_low.values) if bool(v)]

    n = len(close)
    entries = np.zeros(n, dtype=bool)
    stop_price = np.full(n, np.nan)
    target_price = np.full(n, np.nan)

    for k in range(1, len(swing_idx)):
        i_prev, i_cur = swing_idx[k - 1], swing_idx[k]
        if i_cur - i_prev > lookback_bars or i_cur - i_prev < 2:
            continue
        price_prev, price_cur = close.iloc[i_prev], close.iloc[i_cur]
        wad_prev, wad_cur = wad.iloc[i_prev], wad.iloc[i_cur]
        # bullish divergence: price lower low, WAD higher low
        if price_cur < price_prev and wad_cur > wad_prev:
            swing_high = close.iloc[i_prev:i_cur + 1].max()
            search_end = min(i_cur + lookback_bars, n)
            for j in range(i_cur + 1, search_end):
                if close.iloc[j] > swing_high:
                    entries[j] = True
                    a = atr.iloc[i_cur]
                    if pd.notna(a) and a > 0:
                        stop_price[j] = price_cur - a
                        risk = close.iloc[j] - stop_price[j]
                        target_price[j] = close.iloc[j] + reward_risk * risk
                    break

    pos_vals = np.zeros(n, dtype=int)
    in_pos = False
    entry_i = 0
    cur_stop = np.nan
    cur_target = np.nan
    for i in range(n):
        px = close.iloc[i]
        if in_pos:
            bars_held = i - entry_i
            if (pd.notna(cur_stop) and px <= cur_stop) or (
                pd.notna(cur_target) and px >= cur_target
            ) or bars_held >= max_hold_bars:
                in_pos = False
        if not in_pos and entries[i]:
            in_pos = True
            entry_i = i
            cur_stop = stop_price[i]
            cur_target = target_price[i]
        pos_vals[i] = 1 if in_pos else 0

    return pd.Series(pos_vals, index=close.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    lookback_bars: int = 30,
    atr_window: int = 14,
    reward_risk: float = 2.0,
    max_hold_bars: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        swing_window=swing_window,
        lookback_bars=lookback_bars,
        atr_window=atr_window,
        reward_risk=reward_risk,
        max_hold_bars=max_hold_bars,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = (position.shift(1).fillna(0) * daily_ret).fillna(0.0)
    return strat_ret
