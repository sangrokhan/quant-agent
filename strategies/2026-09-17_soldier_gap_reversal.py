"""Strategy: D'Ambrosio/Star modified "Soldier" gap-reversal candle (TASC Oct 2017).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-144):
Jerry D'Ambrosio and Barbara Star's TASC Oct 2017 article "A Candlestick
Strategy With Soldiers And Crows" introduces a MODIFIED (fewer-candle, more
frequent) variant of the classic "three white soldiers" reversal pattern.
Unlike the classic pattern (3 consecutive higher closes -- already tested
and rejected in this repo at id=2026-09-06-132), the source's own
_C_Soldier function requires only ONE specific reversal candle occurring
after a 3-bar downtrend context:
    Close[1] < Close[2]  AND  Close[2] < Close[3]   (2-bar prior downtrend)
    Close[1] < Open[1]                              (prior bar was bearish)
    Open  > Close[1]                                (today gaps up from
                                                       yesterday's close)
    Close > Open[1]                                 (today closes above
                                                       yesterday's open --
                                                       full reversal)
    Open  < Open[1]                                 (but today's open is
                                                       still below
                                                       yesterday's open)
This is a genuinely distinct mechanical trigger from the classic 3-bar
staircase pattern: it's a single strong reversal candle validated by a
2-bar downtrend context and a specific gap/close relationship to the prior
bar, not three consecutive higher closes. Source's own rationale: "the
modified patterns require fewer candles and as a result occur more
frequently" and are "useful for highlighting reversals."

Source itself (TradeStation PaintBar/Scanner code) doesn't specify an
entry/exit trading rule (it's a scanner/indicator only) -- our own addition,
flagged as such: long entry on the bar AFTER the Soldier pattern confirms
(next bar open), exit on a mean-reversion target (close crosses back above
a short SMA) or a max_hold_days time-stop, gated optionally by a minimum
average-volume filter (source's own MinAvgVolume/VolAvgLength inputs,
included here as min_avg_volume_pct -- a fraction of the trailing average
we require current volume to exceed, since exact dollar volume floors
don't generalize across equity/crypto).

Source: https://traders.com/Documentation/FEEDbk_docs/2017/10/TradersTips.html
(TradeStation section, read via browser_exec).

Interface contract for validators (see validation/validators.py):
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


def generate_signals(
    price_df: pd.DataFrame,
    exit_sma_window: int = 5,
    max_hold_days: int = 10,
    vol_avg_length: int = 50,
    min_avg_volume_pct: float = 0.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]
    volume = df["volume"]

    c1 = close.shift(1)
    c2 = close.shift(2)
    c3 = close.shift(3)
    o1 = open_.shift(1)

    soldier = (
        (c1 < c2)
        & (c2 < c3)
        & (c1 < o1)
        & (open_ > c1)
        & (close > o1)
        & (open_ < o1)
    )

    if min_avg_volume_pct > 0:
        avg_vol = volume.rolling(vol_avg_length).mean()
        vol_ok = volume >= (avg_vol * min_avg_volume_pct)
        soldier = soldier & vol_ok.fillna(False)

    entry = soldier.fillna(False)

    exit_sma = close.rolling(exit_sma_window).mean()
    exit_meanrev = close > exit_sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
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
