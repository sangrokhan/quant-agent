"""Strategy: Relative Momentum Index (RMI) oversold-recovery mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-013):
The Relative Momentum Index (RMI, Roger Altman) is an RSI variant that
counts "up"/"down" periods by comparing today's close to close
momentum_period days ago (rather than the 1-day change RSI uses), making
it a hybrid of RSI's oscillator math with a momentum lookback. Per
NewTraderU's disclosure, it oscillates 0-100 with the standard RSI-style
overbought=70/oversold=30 convention, and is noted as most effective in
range-bound markets. This iteration tests the mechanical analog of
Larry Connors' RSI(2) mean-reversion rule (already accepted in this repo,
id=2026-09-03-005) but substituting RMI for RSI: long when close > SMA
trend filter AND RMI drops to/below an oversold threshold, exit when RMI
recovers back above an exit threshold, or a max_hold_days time-stop.

First RMI strategy in this repo -- distinct from RSI(2) itself (uses
period-to-period gains/losses, momentum_period effectively =1) and from
Connors RSI (id=2026-09-04-113, a composite of THREE different
sub-indicators, not RMI's single momentum-lookback RSI variant).

Formula (per NewTraderU / standard RMI definition):
  up_move_t = max(close_t - close_{t-momentum_period}, 0)
  down_move_t = max(close_{t-momentum_period} - close_t, 0)
  avg_up = EMA/Wilder-smoothed average of up_move over rmi_period
  avg_down = EMA/Wilder-smoothed average of down_move over rmi_period
  RMI = 100 - 100 / (1 + avg_up/avg_down)

Signal logic
------------
- Entry (long): close > SMA(trend_window) (uptrend filter, matching the
  RSI(2)-strategy convention already validated in this repo) AND RMI
  closes at/below oversold_threshold (30 standard, tested lower too).
- Exit: RMI closes back above exit_threshold, OR the trend filter
  breaks, OR a max_hold_days time-stop backstop.
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


def _rmi(close: pd.Series, momentum_period: int, rmi_period: int) -> pd.Series:
    momentum = close.diff(momentum_period)
    up_move = momentum.clip(lower=0.0)
    down_move = (-momentum).clip(lower=0.0)

    # Wilder-style smoothing (matches standard RSI/RMI convention).
    avg_up = up_move.ewm(alpha=1.0 / rmi_period, adjust=False, min_periods=rmi_period).mean()
    avg_down = down_move.ewm(alpha=1.0 / rmi_period, adjust=False, min_periods=rmi_period).mean()

    rs = avg_up / avg_down.replace(0.0, 1e-9)
    rmi = 100.0 - (100.0 / (1.0 + rs))
    return rmi


def generate_signals(
    price_df: pd.DataFrame,
    momentum_period: int = 5,
    rmi_period: int = 14,
    trend_window: int = 200,
    oversold_threshold: float = 30.0,
    exit_threshold: float = 50.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rmi = _rmi(close, momentum_period, rmi_period)
    trend_sma = close.rolling(trend_window, min_periods=max(2, trend_window // 2)).mean()
    trend_ok = close > trend_sma

    entry = (rmi <= oversold_threshold) & trend_ok.fillna(False)
    exit_signal = (rmi >= exit_threshold) | (~trend_ok.fillna(False))

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
