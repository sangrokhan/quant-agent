"""Strategy: RSI Hidden Bullish Divergence -- trend-continuation pullback entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-003):
Per AlchemyMarkets' "Hidden Bullish Divergence Comprehensive Guide"
(https://alchemymarkets.com/education/strategies/hidden-bullish-divergence/,
mechanical definition fully disclosed): in an established uptrend (higher
highs / higher lows), a pullback swing low where PRICE prints a HIGHER low
while the RSI oscillator prints a LOWER low (at the corresponding swing) is
a "hidden bullish divergence" -- a trend-CONTINUATION signal, not a
reversal signal like a classic/regular divergence. The source's own
explanation: momentum weakens on the pullback (RSI lower low) but demand
absorbs the selling before price actually makes a new low (price higher
low), consistent with the uptrend remaining intact. This is a genuinely
new construction in this repo -- every prior divergence strategy tested
here (2026-09-03-019 RSI classic bullish divergence, 2026-09-04-088 OBV
divergence, 2026-09-05-047 CMF divergence, 2026-09-05-048 Force Index
divergence, 2026-09-05-057 RVI divergence, 2026-09-04-160 Awesome
Oscillator Twin Peaks) tests REGULAR/classic divergence (price lower low +
oscillator higher low, a reversal signal at the END of a downtrend). This
is the mirror-image HIDDEN divergence construction (price higher low +
oscillator lower low, a continuation signal DURING an uptrend pullback),
never tested in this repo before.

Signal logic
------------
- Uptrend filter: close > SMA(trend_window) (long-term uptrend context).
- Swing lows detected via a simple local-minimum rule: bar i is a swing low
  if close[i] is the minimum of the window [i-swing_lookback, i+swing_lookback].
- Compare the current confirmed swing low to the PREVIOUS confirmed swing
  low: hidden bullish divergence when price's swing low is HIGHER than the
  prior swing low's price, AND RSI's value at the current swing low is
  LOWER than RSI's value at the prior swing low.
- Entry (long): on the bar the divergence is confirmed (swing low
  confirmed swing_lookback bars after the low itself, avoiding lookahead)
  AND close > SMA(trend_window).
- Exit: close falling below the divergence swing-low's price (failed
  continuation), the trend filter breaking (close < SMA(trend_window)), or
  a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
"""

from __future__ import annotations

import numpy as np
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
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _swing_lows(close: pd.Series, lookback: int) -> np.ndarray:
    """Return boolean array marking bars that are a local minimum over
    [i-lookback, i+lookback] -- confirmed only `lookback` bars AFTER the low
    (no lookahead in the signal computed at confirmation time)."""
    n = len(close)
    vals = close.values
    is_low = np.zeros(n, dtype=bool)
    for i in range(lookback, n - lookback):
        window = vals[i - lookback : i + lookback + 1]
        if vals[i] == window.min():
            is_low[i] = True
    return is_low


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    swing_lookback: int = 5,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    rsi = _rsi(close, rsi_window)
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    is_low = _swing_lows(close, swing_lookback)
    low_indices = np.where(is_low)[0]

    # Confirmation bar index = swing bar index + swing_lookback (that's when
    # we can know it was a local min, since it needed swing_lookback bars
    # AFTER it to confirm).
    divergence_confirm_bar = np.zeros(n, dtype=bool)
    divergence_swing_price = np.full(n, np.nan)

    prev_low_idx = None
    for idx in low_indices:
        confirm_idx = idx + swing_lookback
        if confirm_idx >= n:
            continue
        if prev_low_idx is not None:
            price_higher_low = close.iloc[idx] > close.iloc[prev_low_idx]
            rsi_lower_low = rsi.iloc[idx] < rsi.iloc[prev_low_idx]
            if price_higher_low and rsi_lower_low:
                divergence_confirm_bar[confirm_idx] = True
                divergence_swing_price[confirm_idx] = close.iloc[idx]
        prev_low_idx = idx

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_count = 0
    stop_price = None
    for i in range(n):
        if in_position:
            hold_count += 1
            close_i = close.iloc[i]
            if (stop_price is not None and close_i < stop_price) or (not uptrend.iloc[i]) or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                stop_price = None
            else:
                position.iloc[i] = 1
        else:
            if divergence_confirm_bar[i] and uptrend.iloc[i]:
                in_position = True
                hold_count = 0
                stop_price = divergence_swing_price[i]
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    swing_lookback: int = 5,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        rsi_window=rsi_window,
        swing_lookback=swing_lookback,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(float) * daily_returns
    return strat_returns
