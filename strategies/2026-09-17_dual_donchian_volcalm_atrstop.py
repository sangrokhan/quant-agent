"""Strategy: Dual-Length Donchian Breakout with Volatility-Calm Entry Filter
and ATR Stop-Loss ("The Degree Of Complexity", Oscar Cagigas, TASC February
2014). Read this iteration via browser_exec at
https://traders.com/documentation/feedbk_docs/2014/02/traderstips.html
(EasyLanguage code disclosed directly in the article's TradeStation Traders'
Tips code section, credited to Doug McCrary/TradeStation Securities).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-116):
Cagigas's "complex" 4-parameter system uses a WIDER Donchian channel for
ENTRY (entry_channel_length, default 40) than for EXIT (exit_channel_length,
default 15) -- an asymmetric breakout/exit-band width distinct from this
repo's existing single-length Donchian/Turtle entries. Crucially it also
gates entries with an "EntryVolOK" filter that only allows a NEW entry when
TODAY's single-bar true range is BELOW atr_vol_coef (default 0.9) times
yesterday's smoothed ATR -- i.e. entries are SKIPPED right after a volatility
spike, the opposite of most vol-breakout strategies that require elevated
volatility to confirm a breakout. The hypothesis is that this contrarian
"wait for calm before breaking out" filter, combined with the wider
entry/narrower exit asymmetry and an ATR-based hard stop, produces a more
robust trend-following system than this repo's existing symmetric Donchian
variants (e.g. donchian_breakout_trend.py, donchian_turtle_breakout.py).
Long-only adaptation tested here (source is long/short).

Exact formula (from TASC Feb 2014 TradeStation EasyLanguage, as read this
iteration):
    UpperEntryChannel = Highest(High, entry_channel_length)
    LowerExitChannel  = Lowest(Low, exit_channel_length)
    StopATR    = ATR(atr_length)                 (Wilder-style ATR)
    EntryVolOK = TrueRange(today) < StopATR[yesterday] * atr_vol_coef
    Long entry: EntryVolOK AND High crosses over UpperEntryChannel[1]
    Long exit:  Low crosses under LowerExitChannel[1]
                OR Close <= EntryPrice - StopATR * atr_stop_mult (ATR stop)

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr


def generate_signals(
    price_df: pd.DataFrame,
    entry_channel_length: int = 40,
    exit_channel_length: int = 15,
    atr_length: int = 20,
    atr_vol_coef: float = 0.9,
    atr_stop_mult: float = 4.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series (long-only adaptation of
    Cagigas's dual-Donchian breakout system)."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    upper_entry = high.rolling(entry_channel_length).max()
    lower_exit = low.rolling(exit_channel_length).min()

    tr = _true_range(df)
    stop_atr = tr.ewm(alpha=1.0 / atr_length, adjust=False, min_periods=atr_length).mean()

    entry_vol_ok = (tr < stop_atr.shift(1) * atr_vol_coef) if atr_vol_coef != 0 else pd.Series(True, index=df.index)
    breakout = high > upper_entry.shift(1)
    entry = entry_vol_ok.fillna(False) & breakout.fillna(False)

    exit_channel_break = low < lower_exit.shift(1)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_price = None
    for i in range(len(df)):
        if in_position:
            atr_stop_hit = (
                atr_stop_mult != 0
                and entry_price is not None
                and not pd.isna(stop_atr.iloc[i])
                and close.iloc[i] <= entry_price - stop_atr.iloc[i] * atr_stop_mult
            )
            if bool(exit_channel_break.iloc[i]) or atr_stop_hit:
                in_position = False
                entry_price = None
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_price = float(close.iloc[i])
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
