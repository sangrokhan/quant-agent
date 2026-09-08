"""Strategy: Dual-EMA crossover + RSI-midline confirmation, low-vol regime gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-169):
Direct follow-up to near-miss 2026-09-04-165 (dual-EMA(20/50) crossover with
RSI(14)>50 midline confirmation, QQQ full-sample Sharpe 0.930 near-miss, MDD/
TC-survival/param-sensitivity all pass on QQQ; grid pass_fraction spread
across regimes 13/32 low, 9/32 mid, 1/32 high). Per the same fix pattern
already validated in this repo for KAMA/ATR-band (2026-09-06-183), VQI
streak (2026-09-08-044), and this cron trigger's own Range Filter [DW]
(2026-09-08-168), adds an entry-only realized-volatility regime gate (20d
realized vol <= trailing 252d median) to the identical dual-EMA + RSI-
midline entry/exit logic, isolating whether the gate alone rescues the
near-miss. NOTE: unlike the ASI swing-channel attempt (2026-09-08-097,
rejected -- gate didn't help because the base edge was too weak overall),
this candidate's grid pass distribution (13/9/1 across low/mid/high) is
LESS concentrated than Range Filter [DW]'s (36/18/1), so the outcome here is
genuinely uncertain going in -- a real test of the fix pattern's limits, not
a guaranteed rescue.

Signal logic
------------
- Fast EMA(20) crossing above slow EMA(50) is the base entry trigger.
- Confirmation: RSI(14) must be above its 50 midline at the crossover bar
  (broad bullish momentum regime, not overbought/oversold usage).
- Additional gate (new this iteration): only allow NEW entries when 20-day
  realized volatility of daily log returns is <= its own trailing 252-day
  median (low-vol regime), identical construction to the repo's other
  vol-gated strategies.
- Exit: reverse EMA cross, RSI dropping below 50, or a max_hold_days
  time-stop -- unchanged from the original 2026-09-04-165 rule.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


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
    fast_span: int = 20,
    slow_span: int = 50,
    rsi_period: int = 14,
    rsi_midline: float = 50.0,
    max_hold_days: int = 30,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_ema = close.ewm(span=fast_span, adjust=False).mean()
    slow_ema = close.ewm(span=slow_span, adjust=False).mean()
    ema_bullish = fast_ema > slow_ema
    ema_cross_up = ema_bullish & ~ema_bullish.shift(1).fillna(False)
    ema_cross_down = (~ema_bullish) & ema_bullish.shift(1).fillna(False)

    rsi = _rsi(close, rsi_period)
    rsi_bullish = rsi > rsi_midline

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = (realized_vol <= (vol_median_1y * vol_regime_ratio)).fillna(False)

    entry = ema_cross_up & rsi_bullish & low_vol_regime
    exit_signal = ema_cross_down | (~rsi_bullish)

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
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
