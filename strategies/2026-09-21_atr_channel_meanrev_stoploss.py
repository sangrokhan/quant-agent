"""Strategy: ATR Channel Mean Reversion with explicit ATR-based stop-loss and
band-anchored take-profit (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per FMZ.com's "ATR Channel Mean Reversion Quantitative Trading Strategy"
(https://www.fmz.com/lang/en/strategy/434995, read via browser_exec this
iteration -- web_extract's configured backend can't fetch page content):
build an ATR channel (EMA basis +/- atr_mult*ATR band). When price breaks
below the lower band (anomaly drop signal), go long at the next bar's open.
Set a protective stop-loss at entry_price - stop_loss_mult*ATR. Take profit
when price recovers to the middle band (EMA) or the upper ATR band,
whichever is reached first; if the current bar's close is below the
previous bar's low, use the previous bar's low as an interim take-profit
level instead (source's own disclosed refinement to avoid holding through
continued weakness).

This repo already has a Keltner-Channel mean-reversion entry (rejected,
id=2026-09-05-074: plain band-touch bounce + SMA trend filter, no explicit
ATR stop-loss) and a Casey-Bands mean-reversion entry (rejected,
id=2026-09-20-133: high/low-anchored bands, no stop-loss mechanic). This
strategy is distinct from both: (1) explicit ATR-multiple stop-loss exit
(neither prior strategy has one), (2) next-bar-open entry timing (source's
specific execution detail, avoids using the same bar's close for both
signal and entry), (3) dual take-profit target (basis-or-upper-band,
whichever price reaches first) rather than a single basis-crossing exit.

Signal logic
------------
- ATR(atr_window) and EMA(atr_window) basis.
- Lower band = EMA - atr_mult*ATR; Upper band = EMA + atr_mult*ATR.
- Entry trigger: previous bar's close < previous bar's lower band (signal
  bar) -> enter long at TODAY's open (next-bar-open execution, avoiding
  look-ahead on the signal bar's own close).
- While in position: stop-loss price = entry_price - stop_loss_mult*ATR
  (ATR value frozen at entry, per source's static risk-sizing convention).
  Exit (at that bar's close, simplification for daily-bar analysis) when:
    * close <= stop_loss_price (stop-out), OR
    * close >= EMA basis OR close >= upper band (take-profit reached), OR
    * a max_hold_days time-stop (safety valve not in the source, added per
      this repo's convention to bound worst-case holding period).
- Flat (no position) otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position).
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
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 14,
    atr_mult: float = 2.0,
    stop_loss_mult: float = 1.5,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]

    atr = _atr(df, atr_window)
    ema_basis = close.ewm(span=atr_window, adjust=False).mean()
    lower_band = ema_basis - atr_mult * atr
    upper_band = ema_basis + atr_mult * atr

    signal_bar = close < lower_band  # evaluated on bar i, entry executes at bar i+1's open

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = 0.0
    stop_loss_price = 0.0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            hit_stop = close.iloc[i] <= stop_loss_price
            hit_tp = (close.iloc[i] >= ema_basis.iloc[i]) or (close.iloc[i] >= upper_band.iloc[i])
            if bool(hit_stop) or bool(hit_tp) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            # Enter at this bar's open if the PRIOR bar signaled.
            if i > 0 and bool(signal_bar.iloc[i - 1]):
                atr_at_entry = atr.iloc[i - 1]
                if pd.notna(atr_at_entry) and pd.notna(open_.iloc[i]):
                    in_position = True
                    entry_idx = i
                    entry_price = float(open_.iloc[i])
                    stop_loss_price = entry_price - stop_loss_mult * float(atr_at_entry)
                    position.iloc[i] = 1
                else:
                    position.iloc[i] = 0
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strategy_ret
