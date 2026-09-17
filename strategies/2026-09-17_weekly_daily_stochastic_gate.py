"""Strategy: Weekly & Daily Stochastic regime-gated oversold recovery (Vitali Apirine, TASC Sep 2018).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-153):
Vitali Apirine's TASC Sep 2018 article "Weekly & Daily Stochastics" extends
his own "scale the lengths ~5x to simulate a weekly timeframe on daily-only
data" technique (already used for Weekly & Daily MACD, TASC Dec 2017,
tested and accepted in this repo at 2026-09-17-146) to the classic
stochastic oscillator:
    StochD = %K(DailyLength=14), smoothed by DailySmoothingLength
    StochW = %K(WeeklyLength=70), smoothed by WeeklySmoothingLength
Both stochastics share the same OverBought(80)/OverSold(20)/MidLine(50)
levels. Source discloses only the dual indicator (no explicit trading
rule), but its own text says the approach "allows traders to detect the
state of longer-term trends while looking for entry points and reversals"
-- i.e. use the WEEKLY-proxy stochastic as a trend-regime gate and the
DAILY stochastic for the actual entry timing, an Elder-Triple-Screen-style
multi-timeframe combination.

This is distinct from this repo's existing Elder Triple Screen entry
(2026-09-04-044, rejected -- uses weekly MACD-Histogram SLOPE as the gate,
not a weekly stochastic LEVEL) and Multi-Timeframe RSI alignment
(2026-09-08-136, rejected -- uses actual resampled daily/weekly/monthly
RSI via pandas resampling, not Apirine's own length-scaling technique).
Here BOTH lines are the SAME stochastic construction at different lengths
(not resampled real weekly bars), and the gate is a LEVEL condition
(StochW > MidLine, i.e. weekly-proxy trend bullish) rather than a slope
condition.

Our own addition (flagged, source gives no trading rule): long entry when
StochD crosses above OverSold (daily oversold-recovery signal) while
StochW > MidLine (weekly-proxy regime confirms bullish); exit when StochD
crosses above OverBought (source's own mean-reversion target zone) or the
weekly-proxy regime flips bearish (StochW < MidLine), or a max_hold_days
time-stop backstop.

Source: https://traders.com/Documentation/FEEDbk_docs/2018/09/TradersTips.html
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


def _smoothed_stoch(close: pd.Series, high: pd.Series, low: pd.Series, length: int, smoothing: int) -> pd.Series:
    lowest = low.rolling(length).min()
    highest = high.rolling(length).max()
    rng = (highest - lowest).replace(0, float("nan"))
    stoch_k = (close - lowest) / rng * 100
    return stoch_k.rolling(smoothing).mean()


def generate_signals(
    price_df: pd.DataFrame,
    daily_length: int = 14,
    weekly_length: int = 70,
    daily_smoothing: int = 3,
    weekly_smoothing: int = 3,
    oversold: float = 20.0,
    overbought: float = 80.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    mid_line = (overbought + oversold) * 0.5

    smooth_d = _smoothed_stoch(close, high, low, daily_length, daily_smoothing)
    smooth_w = _smoothed_stoch(close, high, low, weekly_length, weekly_smoothing)

    weekly_bullish = smooth_w > mid_line

    entry = (
        (smooth_d > oversold) & (smooth_d.shift(1) <= oversold) & weekly_bullish.fillna(False)
    )
    exit_overbought = (smooth_d > overbought) & (smooth_d.shift(1) <= overbought)
    exit_regime_flip = ~weekly_bullish

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_overbought.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
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
