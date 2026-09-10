"""Strategy: "Trend Pullback" indicator-stack (EMA bias + EMA pullback + RSI
trigger + MACD confirmation), per indicators101.com's "How To Combine
Multiple Indicators (Without Overloading)" one-tool-per-job framework.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-XXX):
Source article (https://indicators101.com/how-to-combine-multiple-indicators-
without-overloading/) prescribes a 5-job "Stack A - Trend Pullback" combo:
  - Bias/regime: 50 EMA > 200 EMA (longs only, price above 200 EMA)
  - Setup: pullback to the 20 EMA
  - Trigger: RSI(14) dips to 40-50 then closes back above 50
  - Confirmation: MACD line above its zero line at/near entry
  - Volatility/risk: ATR-based stop / trailing exit (approximated here via
    a max holding period + trend-break exit rather than an explicit ATR
    stop-loss level, since generate_returns only tracks a 0/1 position
    series, not intrabar stop fills)
This is distinct from every individual-indicator variant already tested in
this repo (plain EMA crossovers, RSI midline reclaim alone, MACD zero-line
alone) because it requires ALL FOUR conditions to align simultaneously
(bias + setup + trigger + confirmation), which the source explicitly frames
as reducing false signals versus any single indicator alone.

Signal logic
------------
- Bias: EMA(50) > EMA(200) AND close > EMA(200) (uptrend regime).
- Setup: close is currently within `pullback_band` (as a fraction, e.g.
  0.01 = 1%) of the EMA(20) line (a "touch" of the pullback level), OR has
  touched it within the last `pullback_lookback` bars without yet triggering.
- Trigger: RSI(rsi_period) was between `rsi_low`/`rsi_mid` (e.g. 40-50)
  within the last `pullback_lookback` bars, and has now closed back above
  `rsi_mid` (50).
- Confirmation: MACD line (`macd_fast`/`macd_slow` EMA difference) > 0 at
  the trigger bar.
- Entry: bias AND setup (recent pullback touch) AND trigger (RSI reclaim)
  AND confirmation (MACD>0), all at the same bar.
- Exit: close crosses back below EMA(20) (pullback support breaks), OR the
  bias regime breaks (EMA(50)<=EMA(200)), OR a `max_hold_days` time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def generate_signals(
    price_df: pd.DataFrame,
    ema_bias_fast: int = 50,
    ema_bias_slow: int = 200,
    ema_pullback: int = 20,
    pullback_band: float = 0.01,
    pullback_lookback: int = 5,
    rsi_period: int = 14,
    rsi_low: float = 40.0,
    rsi_mid: float = 50.0,
    macd_fast: int = 12,
    macd_slow: int = 26,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema_fast_bias = _ema(close, ema_bias_fast)
    ema_slow_bias = _ema(close, ema_bias_slow)
    ema_pb = _ema(close, ema_pullback)
    rsi = _rsi(close, rsi_period)
    macd_line = _ema(close, macd_fast) - _ema(close, macd_slow)

    bias_ok = (ema_fast_bias > ema_slow_bias) & (close > ema_slow_bias)

    # Setup: price within pullback_band of the 20 EMA at some point in the
    # trailing lookback window.
    near_pullback = (close - ema_pb).abs() / ema_pb.replace(0.0, 1e-12) <= pullback_band
    recent_pullback_touch = near_pullback.rolling(pullback_lookback, min_periods=1).max().astype(bool)

    # Trigger: RSI was in the 40-50 zone recently, and has now reclaimed
    # above rsi_mid (50) on this bar.
    rsi_in_zone = (rsi >= rsi_low) & (rsi <= rsi_mid)
    rsi_zone_recent = rsi_in_zone.shift(1).rolling(pullback_lookback, min_periods=1).max().astype(bool)
    rsi_reclaim = rsi_zone_recent & (rsi > rsi_mid)

    # Confirmation: MACD line above zero.
    macd_confirm = macd_line > 0.0

    entry = bias_ok.fillna(False) & recent_pullback_touch.fillna(False) & rsi_reclaim.fillna(False) & macd_confirm.fillna(False)
    exit_pullback_break = close < ema_pb
    exit_bias_break = ~bias_ok.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_pullback_break.iloc[i]) or bool(exit_bias_break.iloc[i]) or held >= max_hold_days:
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
