"""Strategy: Katsanos Stiffness Indicator threshold-crossover trend
following, with an RSI pullback-recovery entry timing gate (long only).

Hypothesis (knowledge_base id TBD, this cron trigger):
Per Markos Katsanos' own disclosed Stiffness Indicator formula
(https://mkatsanos.com/stiffness-indicator, TASC Nov 2018, AmiBroker code
fully disclosed): a volatility-adjusted moving-average floor
(MA2 = SMA(close, ma_period) - min_std * StDev(close, ma_period)) is
compared against close each bar; Stiffness = 100 * (count of bars over the
trailing `stiff_period` where close stayed above MA2) / stiff_period,
EMA-smoothed by `smooth_span`. Higher Stiffness = a stronger, less-erratic
uptrend (fewer volatility-adjusted-MA penetrations). The author's own
example flags Stiffness>75 as a "strong trend" zone, and the companion
TASC Traders' Tips "Buy pullback" rule adds an RSI pullback-recovery
timing gate (RSI turning up from an oversold dip) rather than buying the
raw threshold cross blindly. This iteration operationalizes: enter long
when Stiffness is already above `stiff_threshold` (75) AND a short-term
RSI dips below `rsi_pullback_level` (40) then recovers back above it
within `confirm_bars` (the source's own "RSI turns up from below 40"
pullback-entry timing within an already-confirmed strong trend). Exit when
Stiffness drops back below `stiff_threshold`, or a time-stop. First
Stiffness Indicator entry in this repo (0 prior KB hits) -- distinct from
every existing trend-strength gauge here because it specifically counts
the FREQUENCY of volatility-adjusted-MA penetrations over a lookback, not
a continuous distance/slope/ratio measure.

Signal logic (long side only)
------------------------------
- MA2 = SMA(close, ma_period) - min_std * StDev(close, ma_period).
- Stiffness_t = EMA(100 * rolling_sum(close > MA2, stiff_period) /
  stiff_period, smooth_span).
- RSI(rsi_period) pullback-recovery: RSI dips below rsi_pullback_level,
  then within confirm_bars crosses back above it.
- Entry: Stiffness > stiff_threshold AND an RSI pullback-recovery
  confirms within the same window.
- Exit: Stiffness drops below stiff_threshold, or `max_hold_days`
  time-stop.

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


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _stiffness(
    close: pd.Series, ma_period: int, min_std: float, stiff_period: int, smooth_span: int
) -> pd.Series:
    sma = close.rolling(ma_period).mean()
    std = close.rolling(ma_period).std()
    ma2 = sma - min_std * std
    above = (close > ma2).astype(float)
    pens = above.rolling(stiff_period).sum()
    stif = 100 * pens / stiff_period
    return stif.ewm(span=smooth_span, adjust=False).mean()


def generate_signals(
    price_df: pd.DataFrame,
    ma_period: int = 100,
    min_std: float = 0.5,
    stiff_period: int = 60,
    smooth_span: int = 2,
    stiff_threshold: float = 75.0,
    rsi_period: int = 5,
    rsi_pullback_level: float = 40.0,
    confirm_bars: int = 5,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    stiffness = _stiffness(close, ma_period, min_std, stiff_period, smooth_span)
    rsi = _rsi(close, rsi_period)

    strong_trend = (stiffness > stiff_threshold).fillna(False)
    below_pullback = (rsi < rsi_pullback_level).fillna(False)
    rsi_recover = (rsi >= rsi_pullback_level) & (~(rsi.shift(1) >= rsi_pullback_level).fillna(False))
    rsi_recover = rsi_recover.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            exit_cond = (not bool(strong_trend.iloc[i])) or (held >= max_hold_days)
            if exit_cond:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if bool(rsi_recover.iloc[i]) and bool(strong_trend.iloc[i]):
            # confirm a pullback occurred within confirm_bars before this recovery
            lookback_start = max(0, i - confirm_bars)
            had_pullback = bool(below_pullback.iloc[lookback_start:i].any())
            if had_pullback:
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
                continue

        position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, leverage_cap: float = 1.0, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret * leverage_cap
    return strategy_ret
