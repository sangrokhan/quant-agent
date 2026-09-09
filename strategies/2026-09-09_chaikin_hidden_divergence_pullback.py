"""Strategy: Chaikin Oscillator hidden bullish divergence, 30/50 SMA pullback zone.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-068):
Per ForexMT4Indicators' "Chaikin Oscillator Hidden Trend Divergence" strategy
(https://forexmt4indicators.com/chaikin-oscillator-hidden-trend-divergence-forex-trading-strategy-for-mt5/,
browser_exec fallback -- Bing returned unrelated Google-support results for
the first query, DuckDuckGo html fallback worked for a follow-up), a
trend-CONTINUATION divergence system: define an uptrend when the 30-period
SMA is above the 50-period SMA and price is above both; wait for price to
pull back into the dynamic 30/50 SMA support band and bounce; confirm the
bounce with a HIDDEN bullish divergence on the Chaikin Oscillator (price
makes a HIGHER low on the pullback while the Chaikin Oscillator makes a
LOWER low over the same swing -- the opposite pattern from a regular
divergence, and per the source's own framing this confirms trend
continuation rather than signaling reversal). This is the first HIDDEN
divergence strategy in this repo -- every prior divergence strategy here
(TRIX/KST/RSI/Ultimate-Oscillator/CCI) tests REGULAR divergence for
reversals, a fundamentally different pattern from hidden divergence's
continuation logic. It's also distinct from the existing
2026-09-04_chaikin_osc_trend_filter.py (id 2026-09-04-093), which uses the
Chaikin Oscillator only for a zero-line-cross trend filter gated by a 200d
SMA, not divergence at all.

Chaikin Oscillator formula (standard):
    MFM = ((close - low) - (high - close)) / (high - low)
    MFV = MFM * volume
    ADL = cumulative sum of MFV
    CO  = EMA(co_fast, ADL) - EMA(co_slow, ADL)   (source's standard 3/10)

Signal logic
------------
- Uptrend/pullback-zone gate: sma_fast(30) > sma_slow(50) AND close is
  within [sma_slow, sma_fast] (the dynamic support band) or above it having
  just touched it within `pullback_lookback` bars (approximated here as:
  close's rolling-min over pullback_lookback dipped into/below the band).
- Swing low detection: local pivot lows on both price (close) and the
  Chaikin Oscillator, found via a simple rolling-window local-minimum test
  over `swing_window` bars.
- Hidden bullish divergence: comparing the most recent confirmed swing low
  to the prior one, price's low is HIGHER (higher low) while the Chaikin
  Oscillator's corresponding low is LOWER (lower low).
- Entry (long): uptrend/pullback-zone gate is active AND a hidden bullish
  divergence was confirmed within the last `divergence_valid_bars` bars AND
  today's close > yesterday's close (bullish momentum candle proxy, since
  we operate on daily OHLC not intrabar patterns).
- Exit: close crosses back below sma_slow(50) (trend-structure break), OR a
  `max_hold_days` time-stop (source uses a fixed 2R take-profit instead;
  this repo consistently substitutes a time-stop for a return-based
  target since generate_returns operates on a continuous daily-return
  series, not discrete R-multiples).
- Flat otherwise; long-only, no shorting (per repo convention / SAFETY.md).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly across a parameter grid).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _chaikin_osc(df: pd.DataFrame, co_fast: int, co_slow: int) -> pd.Series:
    high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]
    rng = (high - low).replace(0, pd.NA)
    mfm = ((close - low) - (high - close)) / rng
    mfm = mfm.fillna(0.0)
    mfv = mfm * volume
    adl = mfv.cumsum()
    co = adl.ewm(span=co_fast, adjust=False).mean() - adl.ewm(span=co_slow, adjust=False).mean()
    return co


def _rolling_local_min_flag(series: pd.Series, window: int) -> pd.Series:
    """True where series[i] is the minimum within a centered window (a pivot low)."""
    half = window // 2
    roll_min = series.rolling(window, center=True, min_periods=window).min()
    return (series == roll_min).fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    co_fast: int = 3,
    co_slow: int = 10,
    sma_fast: int = 30,
    sma_slow: int = 50,
    swing_window: int = 11,
    divergence_valid_bars: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    co = _chaikin_osc(df, co_fast, co_slow)
    ma_fast = close.rolling(sma_fast).mean()
    ma_slow = close.rolling(sma_slow).mean()

    uptrend = ma_fast > ma_slow
    in_pullback_zone = (close <= ma_fast) & (close >= ma_slow * 0.98)
    trend_gate = (uptrend & in_pullback_zone).fillna(False)

    price_pivot_low = _rolling_local_min_flag(close, swing_window)
    co_pivot_low = _rolling_local_min_flag(co, swing_window)
    # A "confirmed swing low" bar for divergence purposes: both series flag
    # a pivot low at the same bar (aligned local minima).
    swing_low = price_pivot_low & co_pivot_low

    price_at_swing = close.where(swing_low)
    co_at_swing = co.where(swing_low)
    price_at_swing_ffill = price_at_swing.ffill()
    co_at_swing_ffill = co_at_swing.ffill()
    prev_price_swing = price_at_swing_ffill.shift(1).where(swing_low).ffill()
    prev_co_swing = co_at_swing_ffill.shift(1).where(swing_low).ffill()

    hidden_bull_div_at_swing = swing_low & (price_at_swing > prev_price_swing) & (
        co_at_swing < prev_co_swing
    )
    # Extend each divergence flag forward for divergence_valid_bars bars.
    div_flag = hidden_bull_div_at_swing.fillna(False)
    div_active = div_flag.rolling(divergence_valid_bars, min_periods=1).max().astype(bool)

    momentum_candle = close > close.shift(1)

    entry = trend_gate & div_active.fillna(False) & momentum_candle.fillna(False)
    exit_trend_break = close < ma_slow

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
