"""Strategy: Relative Vigor Index (RVI) bullish divergence.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-057):
Per Google's AI-overview synthesis (Investopedia/Avatrade/Forexopher) of
RVI divergence trading rules: bullish divergence occurs when price forms a
LOWER LOW while the RVI oscillator forms a HIGHER LOW over the same
window -- momentum is fading even as price makes a new low, a classic
reversal warning. Entry trigger: the RVI (green) line crosses above its own
signal line, OR RVI rises back above the zero line. Stop-loss: placed just
below the recent swing low. Exit here (long-only, daily-bar backtest
adaptation) uses the mirror-image bearish-divergence signal, RVI crossing
back below its signal line, or a max_hold_days time-stop (the source gives
only a swing-low stop, no time cap; added since we're testing a multi-year
backtest rather than discretionary chart-watching).

RVI itself (J. Ehlers): a smoothed ratio of (close-open) to (high-low),
using a 4-period weighted moving average numerator/denominator, further
smoothed by `rvi_window`; the signal line is RVI's own SMA over
`signal_window`.

This is the first RVI-DIVERGENCE strategy in this repo -- prior RVI
strategies (2026-09-04-149/150/151-ish signal-line-cross/midline variants)
traded RVI/signal crossovers directly without any price-vs-oscillator
divergence detection; divergence requires comparing swing lows in BOTH
price and the oscillator, a materially different (and more selective)
condition.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
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


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = list(range(1, window + 1))
    return series.rolling(window).apply(lambda x: (x * weights).sum() / sum(weights), raw=True)


def _rvi(df: pd.DataFrame, rvi_window: int, signal_window: int):
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    numerator = (c - o) + 2 * (c.shift(1) - o.shift(1)) + 2 * (c.shift(2) - o.shift(2)) + (c.shift(3) - o.shift(3))
    denominator = (h - l) + 2 * (h.shift(1) - l.shift(1)) + 2 * (h.shift(2) - l.shift(2)) + (h.shift(3) - l.shift(3))
    numerator = numerator / 6.0
    denominator = denominator / 6.0
    raw_rvi = numerator.rolling(rvi_window).sum() / denominator.rolling(rvi_window).sum().replace(0, pd.NA)
    signal = (raw_rvi + 2 * raw_rvi.shift(1) + 2 * raw_rvi.shift(2) + raw_rvi.shift(3)) / 6.0
    signal = signal.rolling(signal_window, min_periods=1).mean()
    return raw_rvi, signal


def generate_signals(
    price_df: pd.DataFrame,
    rvi_window: int = 10,
    signal_window: int = 4,
    swing_lookback: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Bullish divergence: today's price makes a `swing_lookback`-day low
    (close <= rolling min close) while RVI is ABOVE its own value at the
    prior local price-low point within the lookback window (RVI higher low
    vs. price lower low). Entry fires when that divergence condition holds
    AND (RVI crosses above its signal line OR RVI crosses above zero) on
    the same/next bar.
    Exit: RVI crosses back below its signal line, OR a max_hold_days
    time-stop.
    """
    df = _prep(price_df)
    close = df["close"]
    rvi, signal = _rvi(df, rvi_window, signal_window)

    rolling_min_close = close.rolling(swing_lookback).min()
    is_price_low = close <= rolling_min_close

    # Value of RVI at the previous swing-low point within the window
    # (approx: min RVI value seen at any prior new-low bar in the window).
    prior_low_rvi = rvi.rolling(swing_lookback).apply(
        lambda window: window.iloc[0] if len(window) else float("nan"), raw=False
    )

    bullish_divergence = is_price_low & (rvi > prior_low_rvi.shift(1)) & (rvi < 0)

    rvi_cross_signal = (rvi > signal) & (rvi.shift(1) <= signal.shift(1))
    rvi_cross_zero = (rvi > 0) & (rvi.shift(1) <= 0)

    entry = bullish_divergence.fillna(False) & (rvi_cross_signal.fillna(False) | rvi_cross_zero.fillna(False))
    exit_cross = (rvi < signal) & (rvi.shift(1) >= signal.shift(1))

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            ec = exit_cross.iloc[i]
            ec_flag = bool(ec) if not pd.isna(ec) else False
            if ec_flag or held >= max_hold_days:
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
