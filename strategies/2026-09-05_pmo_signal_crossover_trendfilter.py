"""Strategy: DecisionPoint Price Momentum Oscillator (PMO) signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-010):
Carl Swenlin's DecisionPoint Price Momentum Oscillator (PMO) is a
double-smoothed 1-period rate-of-change oscillator. Per StockCharts
ChartSchool's full formula disclosure, the PMO Line is a 20-period custom
EMA-style smoothing of (10 * a 35-period custom smoothing of the daily
pct-change), and the PMO Signal Line is a standard 10-period EMA of the
PMO Line. The classic mechanical rule (analogous to MACD signal-line
crossovers, which the source explicitly likens the PMO to) is: PMO
crossing above its Signal Line is a bullish momentum-shift long entry,
crossing back below is the exit. Gated here by a long-term SMA trend
filter (close > SMA(trend_window)) since the PMO alone is a pure
momentum measure with no trend-direction context of its own -- a
standard pairing used by several other momentum-oscillator strategies
already tested in this repo (e.g. PPO id=2026-09-04-109, similarly
MACD-like).

First PMO strategy in this repo -- distinct from MACD (uses two plain
EMAs of price, not an EMA of a ROC-normalized ratio) and from PPO
(id=2026-09-04-109, uses EMA(12)/EMA(26) ratio, not PMO's custom
double-smoothed 1-day-ROC construction). The PMO's ratio-based
construction is explicitly normalized (unlike MACD's absolute price
units), which the source notes makes it comparable across securities --
not exploited here, just noted as the key methodological distinction.

Formula (per StockCharts ChartSchool, exact):
  smoothing_multiplier(n) = 2 / n
  custom_smooth(x, n)_t = (x_t - custom_smooth(x,n)_{t-1}) * (2/n)
                            + custom_smooth(x,n)_{t-1}
  roc_pct_t = 100 * (close_t / close_{t-1} - 1)
  pmo_line = custom_smooth(10 * custom_smooth(roc_pct, roc_smooth_period=35), pmo_smooth_period=20)
  pmo_signal = EMA(pmo_line, signal_period=10)   [true EMA, not custom-smooth]

Signal logic
------------
- Entry (long): PMO crosses above pmo_signal AND close > SMA(trend_window)
  (uptrend gate).
- Exit: PMO crosses below pmo_signal, OR the trend filter breaks (close
  falls below SMA(trend_window)), OR a max_hold_days time-stop backstop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _custom_smooth(x: pd.Series, n: int) -> pd.Series:
    """PMO's custom EMA-like smoothing: multiplier=2/n (no +1, unlike a
    true EMA's 2/(n+1)). Seeded with the first available value."""
    mult = 2.0 / n
    out = pd.Series(index=x.index, dtype=float)
    first_valid = x.first_valid_index()
    if first_valid is None:
        return out
    start_pos = x.index.get_loc(first_valid)
    out.iloc[start_pos] = x.iloc[start_pos]
    for i in range(start_pos + 1, len(x)):
        prev = out.iloc[i - 1]
        xi = x.iloc[i]
        if pd.isna(xi):
            out.iloc[i] = prev
            continue
        out.iloc[i] = (xi - prev) * mult + prev
    return out


def _pmo(close: pd.Series, roc_smooth_period: int, pmo_smooth_period: int, signal_period: int):
    roc_pct = 100.0 * (close / close.shift(1) - 1.0)
    smoothed_roc = _custom_smooth(roc_pct, roc_smooth_period) * 10.0
    pmo_line = _custom_smooth(smoothed_roc, pmo_smooth_period)
    pmo_signal = pmo_line.ewm(span=signal_period, adjust=False).mean()
    return pmo_line, pmo_signal


def generate_signals(
    price_df: pd.DataFrame,
    roc_smooth_period: int = 35,
    pmo_smooth_period: int = 20,
    signal_period: int = 10,
    trend_window: int = 200,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    pmo_line, pmo_signal = _pmo(close, roc_smooth_period, pmo_smooth_period, signal_period)
    trend_sma = close.rolling(trend_window, min_periods=max(2, trend_window // 2)).mean()
    trend_ok = close > trend_sma

    above = pmo_line > pmo_signal
    cross_up = above & (~above.shift(1).fillna(False))
    cross_down = (~above) & above.shift(1).fillna(False)

    entry = cross_up & trend_ok.fillna(False)
    exit_signal = cross_down | (~trend_ok.fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
    daily_ret = position.shift(1).fillna(0) * close.pct_change().fillna(0.0)
    return daily_ret
