"""Strategy: TPS scale-in with steeper scale-in weights and higher position
cap (rescue attempt for near-miss 2026-09-06-185).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-186):
Direct follow-up to near-miss 2026-09-06-185 (TPS Connors scale-in,
QQQ full-sample Sharpe 0.871, very low MDD 0.070, very stable parameter
sensitivity 0.086 -- flagged as worth revisiting via steeper scale-in
weights to capture more upside). This variant tests the exact suggested
rescue: change the scale-in schedule from the source's original
10/20/30/40 (cumulative 10/30/60/100%) to a steeper 10/25/35/50 (cumulative
10/35/70/120% capped at 100%), reaching full position size one day earlier
on average, hypothesizing that capturing more of the eventual mean-reversion
bounce (by being more heavily positioned sooner during the pullback)
improves the Sharpe without materially increasing drawdown, since the
underlying entry/exit trigger logic (200d EMA trend filter, 2-period RSI
oversold entry, RSI>70 exit) is unchanged and already validated as
low-drawdown.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    trend_ema_window: int = 200,
    rsi_window: int = 2,
    rsi_entry_threshold: float = 25.0,
    rsi_exit_threshold: float = 70.0,
    scale_in_weights: tuple = (0.10, 0.25, 0.35, 0.50),
    max_scale_in_days: int = 3,
) -> pd.Series:
    """Return a fractional [0,1] position-weight series."""
    df = _prep(price_df)
    close = df["close"]

    trend_ema = close.ewm(span=trend_ema_window, adjust=False).mean()
    uptrend = close > trend_ema

    rsi = _rsi(close, rsi_window)
    oversold_2day = (rsi < rsi_entry_threshold) & (rsi.shift(1) < rsi_entry_threshold)
    entry_trigger = (oversold_2day & uptrend).fillna(False)
    exit_trigger = (rsi > rsi_exit_threshold).fillna(False)

    weight = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    current_weight = 0.0
    last_entry_price = None
    scale_ins_done = 0

    for i in range(len(close)):
        px = close.iloc[i]
        if in_position:
            if bool(exit_trigger.iloc[i]):
                in_position = False
                current_weight = 0.0
                last_entry_price = None
                scale_ins_done = 0
                weight.iloc[i] = 0.0
                continue
            if scale_ins_done < max_scale_in_days and (last_entry_price is not None) and px < last_entry_price:
                current_weight = min(1.0, current_weight + scale_in_weights[scale_ins_done + 1])
                last_entry_price = px
                scale_ins_done += 1
            weight.iloc[i] = current_weight
        else:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                current_weight = scale_in_weights[0]
                last_entry_price = px
                scale_ins_done = 0
                weight.iloc[i] = current_weight
            else:
                weight.iloc[i] = 0.0
    return weight


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    weight = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = weight.shift(1).fillna(0) * daily_ret
    return strategy_ret
