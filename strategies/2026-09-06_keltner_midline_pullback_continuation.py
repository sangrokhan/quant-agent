"""Strategy: Keltner Channel middle-line pullback (trend continuation).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-136):
Per ThinkMarkets' Keltner Channel guide: "Common ATR Keltner trading
strategies include the trend pullback (buying dips to the middle line in
an uptrend)". This is the THIRD distinct Keltner Channel interpretation
tested in this repo: (1) breakout above upper band (2026-09-03-016,
accepted QQQ-only), (2) mean-reversion bounce off the lower band
(2026-09-05-074, rejected), and now (3) trend-continuation pullback TO
the middle EMA line while the broader trend remains up -- a fundamentally
different entry location (the middle, not either outer band) and
different regime requirement (an established uptrend must already be in
place, unlike the mean-reversion variant which trades against the
prevailing short-term direction).

Signal logic
------------
- Keltner basis = EMA(kc_window); bands = basis +/- kc_mult * ATR(kc_window).
- Uptrend gate: close > SMA(trend_window) (broader trend must be up).
- Entry: close pulls back down to touch/dip below the middle basis line
  (close <= basis) while still in the uptrend gate, then the NEXT bar's
  close recovers back above the basis line (confirms the pullback bounced
  rather than broke down) -- per ThinkMarkets' "buying dips to the middle
  line", the entry is on the bounce confirmation, not the touch itself.
- Exit: close crosses back below the basis line again (failed
  continuation), the uptrend gate breaks (close < SMA(trend_window)), or
  a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series {0,1} long/flat
"""

from __future__ import annotations

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
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window, min_periods=window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    kc_window: int = 20,
    kc_mult: float = 1.5,
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    basis = close.ewm(span=kc_window, min_periods=kc_window, adjust=False).mean()
    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()

    uptrend = close > trend_sma
    touched_basis = close <= basis
    bounce_confirm = (close > basis) & touched_basis.shift(1).fillna(False) & uptrend.shift(1).fillna(False)

    idx = df.index
    n = len(idx)
    pos = pd.Series(0, index=idx, dtype=int)
    in_pos = False
    entry_idx = None

    for i in range(n):
        if in_pos:
            days_held = i - entry_idx
            hit_time = days_held >= max_hold_days
            hit_basis_break = close.iloc[i] < basis.iloc[i]
            hit_trend_break = not bool(uptrend.iloc[i])
            if hit_time or hit_basis_break or hit_trend_break:
                in_pos = False
            else:
                pos.iloc[i] = 1
                continue
        else:
            if bool(bounce_confirm.iloc[i]) and bool(uptrend.iloc[i]):
                in_pos = True
                entry_idx = i
                pos.iloc[i] = 1

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    kc_window: int = 20,
    kc_mult: float = 1.5,
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        kc_window=kc_window,
        kc_mult=kc_mult,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret
