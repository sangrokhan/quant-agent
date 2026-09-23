"""Strategy: ATR liquidity sweep + horizon confirm, RESCUED with an RSI-divergence
confirmation filter at the swept pivot (long side only).

Hypothesis (knowledge_base id TBD, this cron trigger):
Direct rescue attempt for this repo's own recorded near-miss 2026-09-23-046
(ATR-thresholded liquidity sweep + fixed-horizon reversal confirmation,
strategies/2026-09-23_atr_liquidity_sweep_horizon_confirm.py, best full-sample
Sharpe 0.880 on SPY, MDD/TC both pass). That near-miss's own follow-up
rescue attempt (2026-09-23-047, low-vol-regime gate) improved every symbol's
Sharpe but still failed to clear 1.0 anywhere. This iteration tries a
DIFFERENT, not-yet-attempted lever from the source material that inspired
the original hypothesis: TradingView's "Stop Hunter | Liquidity Sweep &
Retest Strategy" (Editors' Pick, read this iteration via browser_exec)
explicitly lists RSI divergence against the RSI reading AT THE ORIGINAL
PIVOT as one of its four confirmation-score components -- a dimension the
prior two attempts in this repo (2026-09-23-046/047) never tested (they
only varied swing_window/poke_atr_mult/confirm_bars/vol_regime_ratio).
This adds that confirmation: a sweep only qualifies as an entry candidate
if, at the confirmation bar, RSI(rsi_window) is HIGHER than RSI was at the
original swing-low pivot bar (bullish momentum divergence -- price made a
new/matching low but momentum did not), filtering out sweeps where the
reversal isn't backed by genuine momentum improvement.

Signal logic
------------
- Identical swing-low/ATR-poke/close-back-above-level/confirm_bars
  mechanism as 2026-09-23-046.
- NEW: at the swing-low pivot bar (the bar establishing swing_low, i.e.
  bar i - swing_window one bar before the rolling-min window closes) AND
  at the confirmation bar, compute RSI(rsi_window). Require
  RSI(confirmation bar) > RSI(pivot bar) + divergence_margin (bullish
  divergence: price near/below the old low, but momentum improving).
- Exit: max_hold_days time-stop OR close falls back below swing_low.
- Optional close>SMA(trend_window) uptrend gate (default True).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


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
    return tr.rolling(window).mean()


def _wilder_rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 10,
    poke_atr_mult: float = 0.5,
    confirm_bars: int = 3,
    max_hold_days: int = 8,
    atr_window: int = 14,
    trend_window: int = 200,
    trend_filter: bool = True,
    rsi_window: int = 14,
    divergence_margin: float = 2.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    n = len(close)

    swing_low = low.rolling(swing_window).min().shift(1)
    # Index (bar offset) of the pivot bar establishing each swing_low value:
    # the argmin within the trailing swing_window-bar lookback (shifted by 1
    # to match swing_low's own shift(1) no-look-ahead convention).
    pivot_offset = low.rolling(swing_window).apply(lambda x: x.argmin(), raw=True).shift(1)

    atr = _atr(df, atr_window)
    poke = (low < (swing_low - poke_atr_mult * atr)).fillna(False)

    rsi = _wilder_rsi(close, rsi_window)

    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False) if trend_filter else pd.Series(True, index=close.index)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    i = 0
    while i < n:
        if in_position:
            held = i - entry_idx
            invalidated = bool(close.iloc[i] < swing_low.iloc[i]) if pd.notna(swing_low.iloc[i]) else False
            if invalidated or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                i += 1
                continue
            position.iloc[i] = 1
            i += 1
            continue

        if bool(poke.iloc[i]) and pd.notna(swing_low.iloc[i]) and bool(uptrend.iloc[i]):
            level = swing_low.iloc[i]
            offset = pivot_offset.iloc[i]
            pivot_bar_idx = i - swing_window + int(offset) if pd.notna(offset) else None
            pivot_rsi = rsi.iloc[pivot_bar_idx] if pivot_bar_idx is not None and 0 <= pivot_bar_idx < n else None

            confirmed_at = None
            for j in range(i, min(i + confirm_bars + 1, n)):
                if close.iloc[j] > level:
                    if pivot_rsi is not None and pd.notna(pivot_rsi) and pd.notna(rsi.iloc[j]):
                        if rsi.iloc[j] > pivot_rsi + divergence_margin:
                            confirmed_at = j
                            break
                    # if RSI data unavailable, skip divergence requirement
                    elif pivot_rsi is None or pd.isna(pivot_rsi):
                        confirmed_at = j
                        break
            if confirmed_at is not None:
                in_position = True
                entry_idx = confirmed_at
                i = confirmed_at
                position.iloc[i] = 1
                i += 1
                continue
        position.iloc[i] = 0
        i += 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
