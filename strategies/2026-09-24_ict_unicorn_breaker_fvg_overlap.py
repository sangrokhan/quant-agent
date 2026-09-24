"""Strategy: ICT "Unicorn" Model -- Breaker Block + Fair Value Gap overlap entry.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per LuxAlgo's Smart Money Concepts / ICT library page for the "Unicorn"
model (https://www.luxalgo.com/library/concept/unicorn/, read via
browser_exec after web_search DDGS backend intermittently
failed/returned stale results this iteration): a bullish Unicorn setup is a
5-step sequence --
  1. Sweep: price trades below a prior swing low (sell-side liquidity
     grab), then recovers above it.
  2. Displacement: the recovery breaks a prior swing high with an
     energetic move that leaves a 3-candle Fair Value Gap (FVG) -- i.e.
     bar[i-2].high < bar[i].low (a bullish FVG on the displacement leg).
  3. Breaker: the bearish candles carrying price DOWN into the sweep (the
     down-leg immediately preceding the swept low).
  4. Unicorn zone = the price-range OVERLAP between the breaker block's
     range and the FVG's range; if they don't overlap it's not a unicorn.
  5. Entry: wait for price to retrace back INTO that overlap zone and
     treat a decisive close back below the breaker's far (low) side as
     invalidation/stop.

This is a genuinely novel entry-timing construction distinct from every
prior order-block/FVG/liquidity-sweep entry in this repo: those individual
concepts (order block, fair value gap, liquidity sweep, break-of-structure)
have each been tested separately, but never combined into the specific
"breaker+FVG geometric overlap" confluence filter this source defines as
its own distinct concept (explicitly contrasted with a standalone breaker
or a standalone FVG on the source's own comparison table).

Operationalized on daily bars (single-timeframe simplification of the
source's intraday/session-window framing, since data/loaders.py exposes
daily OHLCV; no killzone/session filter applied):
    1. Swing low/high: rolling `swing_window`-bar pivot low/high (a bar is
       a swing low if it's the lowest low in a centered window of that
       size; likewise for swing high). Detected causally with a
       `swing_window`-bar lag so no lookahead.
    2. Sweep: today's low undercuts the most recent confirmed swing low by
       at least `sweep_atr_mult` * ATR(atr_window), THEN a later bar's
       close recovers back above that swept swing low.
    3. Displacement + FVG: within `displacement_window` bars after the
       sweep recovery, close breaks above the most recent confirmed swing
       high AND a 3-bar bullish FVG forms (low[i] > high[i-2]) somewhere in
       that displacement leg.
    4. Breaker block range = the high/low range of the down-leg bar(s)
       immediately preceding the swept swing low (the single bar making
       that swing low, widened by `breaker_lookback` bars back).
    5. Overlap = intersection of the breaker range and the FVG range; must
       be non-empty (a positive-width overlap) to qualify as a unicorn.
    6. Entry (long): price retraces back into the overlap zone (low <=
       overlap_high AND high >= overlap_low) within `retrace_window` bars
       of the displacement leg completing.
    7. Exit: close falls below the breaker's low (source's own
       invalidation rule) OR a `take_profit_atr_mult` * ATR target is hit
       OR a `max_hold_days` time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def _swing_lows_highs(df: pd.DataFrame, swing_window: int):
    low, high = df["low"], df["high"]
    is_swing_low = low == low.rolling(swing_window * 2 + 1, center=True).min()
    is_swing_high = high == high.rolling(swing_window * 2 + 1, center=True).max()
    # Causal lag: a swing pivot is only "confirmed" swing_window bars after it forms.
    is_swing_low = is_swing_low.shift(swing_window).fillna(False)
    is_swing_high = is_swing_high.shift(swing_window).fillna(False)
    return is_swing_low, is_swing_high


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    atr_window: int = 14,
    sweep_atr_mult: float = 0.25,
    displacement_window: int = 10,
    retrace_window: int = 15,
    take_profit_atr_mult: float = 3.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series (bullish Unicorn only)."""
    df = _prep(price_df)
    n = len(df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    atr = _atr(df, atr_window)
    is_swing_low, is_swing_high = _swing_lows_highs(df, swing_window)

    swing_low_idx = np.where(is_swing_low.values)[0]
    swing_high_idx = np.where(is_swing_high.values)[0]

    close_v = close.values
    high_v = high.values
    low_v = low.values
    atr_v = atr.values

    position = np.zeros(n, dtype=int)

    in_position = False
    entry_i = -1
    breaker_low = None
    tp_level = None

    sl_ptr = 0  # pointer into swing_low_idx for "most recent confirmed swing low before i"
    sh_ptr = 0

    for i in range(n):
        if in_position:
            held = i - entry_i
            stop_hit = close_v[i] < breaker_low if breaker_low is not None else False
            tp_hit = high_v[i] >= tp_level if tp_level is not None else False
            if stop_hit or tp_hit or held >= max_hold_days:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
            continue

        # advance pointers to most recent confirmed swing low/high strictly before i
        while sl_ptr < len(swing_low_idx) and swing_low_idx[sl_ptr] < i:
            sl_ptr += 1
        while sh_ptr < len(swing_high_idx) and swing_high_idx[sh_ptr] < i:
            sh_ptr += 1
        prev_sl_pos = sl_ptr - 1
        prev_sh_pos = sh_ptr - 1
        if prev_sl_pos < 0 or prev_sh_pos < 0:
            continue
        recent_sl = swing_low_idx[prev_sl_pos]
        recent_sh = swing_high_idx[prev_sh_pos]
        if np.isnan(atr_v[i]) or atr_v[i] <= 0:
            continue

        swing_low_price = low_v[recent_sl]
        swing_high_price = high_v[recent_sh]

        # 1. Sweep check: within lookback before i, some bar undercut swing_low_price
        # by sweep_atr_mult*ATR then a later close recovered above it.
        lookback_start = max(0, i - displacement_window - retrace_window)
        window_slice = range(lookback_start, i)
        swept = False
        sweep_bar_low_idx = None
        recovered_close_idx = None
        for j in window_slice:
            if j <= recent_sl:
                continue
            if low_v[j] < swing_low_price - sweep_atr_mult * atr_v[i]:
                sweep_bar_low_idx = j
                for k in range(j + 1, min(i, j + displacement_window) + 1):
                    if k < n and close_v[k] > swing_low_price:
                        recovered_close_idx = k
                        swept = True
                        break
                if swept:
                    break

        if not swept or sweep_bar_low_idx is None or recovered_close_idx is None:
            continue

        # 2. Displacement + FVG: close breaks above swing_high_price within
        # displacement_window bars of recovery, and a 3-bar bullish FVG exists.
        disp_end = min(n - 1, recovered_close_idx + displacement_window)
        displacement_confirmed = False
        fvg_low = fvg_high = None
        for k in range(recovered_close_idx, disp_end + 1):
            if close_v[k] > swing_high_price:
                # look for 3-bar FVG ending at or before k: low[m] > high[m-2]
                for m in range(recovered_close_idx + 2, k + 1):
                    if m < n and low_v[m] > high_v[m - 2]:
                        fvg_low, fvg_high = high_v[m - 2], low_v[m]
                        displacement_confirmed = True
                        break
            if displacement_confirmed:
                break

        if not displacement_confirmed or fvg_low is None:
            continue

        # 3. Breaker block = the down-leg bar making the swept swing low.
        breaker_high = high_v[sweep_bar_low_idx]
        breaker_low_val = low_v[sweep_bar_low_idx]

        # 4. Overlap of breaker range and FVG range must be positive-width.
        overlap_low = max(breaker_low_val, fvg_low)
        overlap_high = min(breaker_high, fvg_high)
        if overlap_high <= overlap_low:
            continue

        # 5. Entry: today's bar retraces into the overlap zone.
        if low_v[i] <= overlap_high and high_v[i] >= overlap_low:
            in_position = True
            entry_i = i
            breaker_low = breaker_low_val
            tp_level = close_v[i] + take_profit_atr_mult * atr_v[i]
            position[i] = 1

    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
