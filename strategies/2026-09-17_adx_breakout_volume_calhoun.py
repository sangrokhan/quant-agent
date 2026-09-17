"""Strategy: ADX Breakout with volume confirmation (Ken Calhoun, TASC Mar 2016).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-133):
Per Ken Calhoun's "ADX Breakouts" (TASC Mar 2016; TradeStation EasyLanguage
code disclosed at
https://traders.com/Documentation/FEEDbk_docs/2016/03/TradersTips.html),
a momentum breakout is confirmed when Wilder's ADX(14) crosses above a high
trigger level (40) -- signalling an especially strong directional move just
getting underway -- combined with an above-average volume surge (today's
volume >= 1.1x its 20-day average). The source enters long-next-bar on the
ADX cross with a stop slightly above the breakout bar's close, and suggests
(but does not fully specify) using a trailing stop to manage the exit.

Signal logic
------------
- ADX(adx_length) computed via Wilder's standard recursive smoothing on
  +DM/-DM/TR.
- Volume confirmation: volume >= volume_avg_length-day SMA(volume) *
  volume_multiplier.
- Entry (long): ADX crosses over trigger_level (from <= to >) AND volume
  confirmation holds on the same bar.
- Exit: ADX drops back below exit_level (trend exhaustion, the source's own
  implied logic since ADX>40 is a "special" state that eventually fades),
  OR after a max_hold_days time-stop (this repo's standard safety valve
  since the source's TradeStation code uses a floating trailing stop we
  can't replicate exactly with only OHLCV bars).
- Flat otherwise.

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


def _wilder_adx(df: pd.DataFrame, adx_length: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(0.0, index=df.index)
    minus_dm = pd.Series(0.0, index=df.index)
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[(down_move > up_move) & (down_move > 0)]

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / adx_length, adjust=False, min_periods=adx_length).mean()
    plus_di = 100.0 * (plus_dm.ewm(alpha=1.0 / adx_length, adjust=False, min_periods=adx_length).mean() / atr)
    minus_di = 100.0 * (minus_dm.ewm(alpha=1.0 / adx_length, adjust=False, min_periods=adx_length).mean() / atr)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float("nan"))
    adx = dx.ewm(alpha=1.0 / adx_length, adjust=False, min_periods=adx_length).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    adx_length: int = 14,
    trigger_level: float = 40.0,
    exit_level: float = 25.0,
    volume_avg_length: int = 20,
    volume_multiplier: float = 1.1,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(0.0, index=df.index)

    adx = _wilder_adx(df, adx_length)
    vol_avg = volume.rolling(volume_avg_length).mean()
    volume_ok = volume >= (vol_avg * volume_multiplier)

    adx_cross_over = (adx > trigger_level) & (adx.shift(1) <= trigger_level)
    entry = adx_cross_over.fillna(False) & volume_ok.fillna(False)
    exit_trend_fade = adx < exit_level

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend_fade.iloc[i]) or held >= max_hold_days:
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
