"""Strategy: TTM Squeeze (John Carter) volatility-compression breakout with
momentum-histogram direction, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per stockcharts.com ChartSchool's "TTM Squeeze" page (visited this
iteration via browser_exec, web_search DDGS backend TLS-connection-errored
on the query), John Carter's TTM Squeeze combines a volatility-compression
detector with a directional momentum histogram:

  Squeeze ON when Bollinger Bands (20-period, 2 std) are FULLY inside the
  (original Keltner-1960-formula) Keltner Channel (20-period MA, 1.5x ATR):
      upper_BB < upper_KC  AND  lower_BB > lower_KC
  Squeeze FIRES (turns OFF) the bar the Bollinger Bands expand back outside
  the Keltner Channel -- this is Carter's documented entry trigger: "buying
  on the first green dot [squeeze off] after one or more red dots [squeeze
  on]."

  Momentum histogram: delta = close - mean(Donchian midline over
  momentum_period, SMA(close, momentum_period)); we approximate Carter's
  linear-regression smoothing with an SMA of the delta (a lighter-weight
  same-purpose smoother that preserves sign/direction, since a bar-by-bar
  linear-regression-of-delta reimplementation would exceed the "no
  reimplementing backtest mechanics" scope for a single indicator leg).
  Direction rule per source: enter long only if the momentum histogram is
  ABOVE zero at the fire bar. Exit rule per source: "sell when you've had
  two bars in the new [opposite-direction-of-slope] color" -- approximated
  here as exiting when the histogram has been falling (2 consecutive
  decreases) while still positive, i.e. momentum turning down.

This is a genuinely distinct construction from every other volatility
strategy in this repo: it is the only one that compares TWO DIFFERENT
volatility-band constructions (Bollinger vs. Keltner) against each other as
a squeeze/expansion detector, rather than using either band type alone or a
realized-vol/ATR-level threshold. 0 prior TTM Squeeze entries in this repo.

Interface contract (see validation/validators.py, validation/grid_test.py):
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


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr


def generate_signals(
    price_df: pd.DataFrame,
    bb_period: int = 20,
    bb_std: float = 2.0,
    kc_period: int = 20,
    kc_atr_mult: float = 1.5,
    momentum_period: int = 20,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: squeeze fires (Bollinger Bands were fully inside Keltner
    Channel the prior bar, and expand back outside on this bar) AND the
    momentum histogram is positive at the fire bar.
    Exit: momentum histogram has fallen for 2 consecutive bars (Carter's
    "two bars in the new color" rule) while positive, OR a max_hold_days
    time-stop (source notes moves "tend to last 8-10 bars").
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    sma_bb = close.rolling(bb_period).mean()
    std_bb = close.rolling(bb_period).std()
    upper_bb = sma_bb + bb_std * std_bb
    lower_bb = sma_bb - bb_std * std_bb

    sma_kc = close.rolling(kc_period).mean()
    atr = _true_range(high, low, close).rolling(kc_period).mean()
    upper_kc = sma_kc + kc_atr_mult * atr
    lower_kc = sma_kc - kc_atr_mult * atr

    squeeze_on = (upper_bb < upper_kc) & (lower_bb > lower_kc)
    squeeze_fired = (~squeeze_on) & squeeze_on.shift(1).fillna(False)

    donchian_mid = (high.rolling(momentum_period).max() + low.rolling(momentum_period).min()) / 2.0
    sma_mom = close.rolling(momentum_period).mean()
    delta = close - (donchian_mid + sma_mom) / 2.0
    momentum = delta.rolling(momentum_period // 2 if momentum_period >= 4 else 2).mean()

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    hold_remaining = 0
    falling_count = 0
    mom_vals = momentum.values
    fired_vals = squeeze_fired.values

    for i in range(n):
        if hold_remaining > 0:
            if i >= 2 and not pd.isna(mom_vals[i]) and not pd.isna(mom_vals[i - 1]):
                if mom_vals[i] < mom_vals[i - 1]:
                    falling_count += 1
                else:
                    falling_count = 0
            exit_now = (falling_count >= 2 and mom_vals[i] > 0) or hold_remaining == 1
            position.iloc[i] = 1
            hold_remaining -= 1
            if exit_now:
                hold_remaining = 0
                falling_count = 0
            continue

        if bool(fired_vals[i]) and not pd.isna(mom_vals[i]) and mom_vals[i] > 0:
            position.iloc[i] = 1
            hold_remaining = max_hold_days - 1
            falling_count = 0
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
