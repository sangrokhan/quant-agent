"""Strategy: ADX/DMI (DI+/DI-) crossover, trend-strength gated by an ADX
threshold, with ATR-based stop and 2:1 reward:risk take-profit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-033):
Source: Google AI Overview synthesis (Korean-language SERP, English-language
answer content; search "ADX DI+ DI- crossover trend strategy specific
threshold rule backtest"), read via browser_exec Google SERP fallback
(web_search DDGS backend errored this iteration). Disclosed rule set (J.
Welles Wilder's classic ADX/DMI framework with specific numeric thresholds,
long side only -- this repo's strategies are long/flat 0/1 position series,
no shorting):
  - Long entry: DI+ crosses above DI- (rising bullish momentum) AND ADX >=
    25 (confirms sufficient trend structural force).
  - Exit (either condition):
    - Opposite crossover: DI- crosses back above DI+.
    - Trend regime failure: ADX breaks down below 20.
  - Risk mitigation: 1.5x ATR(14) stop-loss below entry, 2:1 reward:risk
    take-profit target.
No prior entry in this KB uses "ADX DI crossover" with this specific
threshold combination (checked via strategies_index.jsonl grep: zero prior
matches for "ADX DI crossover"; the 48 generic "ADX" mentions use different
mechanisms -- ADX as a standalone trend-strength filter for other
indicators, not a DI+/DI- crossover system with its own ADX>=25 entry gate
and ADX<20 exit gate).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wilder_smooth(series: pd.Series, window: int) -> pd.Series:
    """Wilder's smoothing (equivalent to EWM with alpha=1/window)."""
    return series.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()


def _adx_di(df: pd.DataFrame, window: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    high, low, close = df["high"], df["low"], df["close"]
    prev_high, prev_low, prev_close = high.shift(1), low.shift(1), close.shift(1)

    up_move = high - prev_high
    down_move = prev_low - low

    plus_dm = ((up_move > down_move) & (up_move > 0)).astype(float) * up_move.clip(lower=0)
    minus_dm = ((down_move > up_move) & (down_move > 0)).astype(float) * down_move.clip(lower=0)

    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = _wilder_smooth(tr, window)
    plus_di = 100 * _wilder_smooth(plus_dm, window) / atr.replace(0.0, pd.NA)
    minus_di = 100 * _wilder_smooth(minus_dm, window) / atr.replace(0.0, pd.NA)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, pd.NA)
    adx = _wilder_smooth(dx.fillna(0.0), window)

    return plus_di.fillna(0.0), minus_di.fillna(0.0), adx.fillna(0.0)


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return _wilder_smooth(tr, window)


def generate_signals(
    price_df: pd.DataFrame,
    adx_window: int = 14,
    adx_entry_threshold: float = 25.0,
    adx_exit_threshold: float = 20.0,
    atr_stop_mult: float = 1.5,
    reward_risk: float = 2.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    plus_di, minus_di, adx = _adx_di(df, adx_window)
    atr = _atr(df, adx_window)

    di_bull_cross = (plus_di > minus_di) & (plus_di.shift(1) <= minus_di.shift(1))
    di_bear_cross = (minus_di > plus_di) & (minus_di.shift(1) <= plus_di.shift(1))

    entry_signal = di_bull_cross & (adx >= adx_entry_threshold)

    n = len(close)
    pos_vals = [0] * n
    in_pos = False
    stop_price = None
    target_price = None

    for i in range(n):
        px = close.iloc[i]
        if in_pos:
            exit_now = (
                bool(di_bear_cross.iloc[i])
                or adx.iloc[i] < adx_exit_threshold
                or (stop_price is not None and px <= stop_price)
                or (target_price is not None and px >= target_price)
            )
            if exit_now:
                in_pos = False
                stop_price = None
                target_price = None
        if not in_pos and bool(entry_signal.iloc[i]):
            in_pos = True
            a = atr.iloc[i]
            if pd.notna(a) and a > 0:
                stop_price = px - atr_stop_mult * a
                risk = px - stop_price
                target_price = px + reward_risk * risk
            else:
                stop_price = None
                target_price = None
        pos_vals[i] = 1 if in_pos else 0

    return pd.Series(pos_vals, index=close.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    adx_window: int = 14,
    adx_entry_threshold: float = 25.0,
    adx_exit_threshold: float = 20.0,
    atr_stop_mult: float = 1.5,
    reward_risk: float = 2.0,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        adx_window=adx_window,
        adx_entry_threshold=adx_entry_threshold,
        adx_exit_threshold=adx_exit_threshold,
        atr_stop_mult=atr_stop_mult,
        reward_risk=reward_risk,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = (position.shift(1).fillna(0) * daily_ret).fillna(0.0)
    return strat_ret
