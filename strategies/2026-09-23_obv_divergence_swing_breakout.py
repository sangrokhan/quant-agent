"""Strategy: OBV bullish-divergence swing-breakout with ATR stop / 2R target.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-030):
Source: Google AI Overview synthesis (Korean-language SERP; search "On
Balance Volume OBV divergence trading strategy specific rule backtest"),
read via browser_exec Google SERP fallback (web_search DDGS backend errored
this iteration). Disclosed rule set (long side only implemented here, this
repo's strategies are long/flat 0/1 position series, no shorting):
  - Identify swing lows in price over a lookback window.
  - Bullish divergence: price makes a LOWER low at the most recent swing
    vs. the prior swing low, while OBV makes a HIGHER low at the same two
    points (momentum/volume conviction diverges from price weakness).
  - Trigger/entry: a confirmed bar closes above the swing high between the
    two divergence lows (breakout confirmation, not the divergence point
    itself).
  - Stop-loss: 1x ATR(14) below the divergence low.
  - Take-profit: minimum 1:2 reward:risk (i.e. 2x the entry-to-stop
    distance above entry), OR flat if price never reaches it and instead
    a fresh bearish setup / max holding period passes.
Genuinely new indicator combination for this KB: no prior entry combines
OBV with a swing-based price/volume divergence + ATR risk-defined exit
(checked via strategies_index.jsonl grep: "OBV divergence" / "On Balance
Volume divergence" had zero prior matches).

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


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff().fillna(0.0))
    return (direction * volume).cumsum()


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
    close, volume = df["close"], df["volume"]
    obv = _obv(close, volume)
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
        obv_prev, obv_cur = obv.iloc[i_prev], obv.iloc[i_cur]
        # bullish divergence: price lower low, OBV higher low
        if price_cur < price_prev and obv_cur > obv_prev:
            swing_high = close.iloc[i_prev:i_cur + 1].max()
            # find first confirmed close above swing_high after i_cur
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
