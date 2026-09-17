"""Strategy: Triple Moving-Average Ribbon + MACD Histogram Confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-059):
Per TheIndicatorLab's "Rob_Hoffman_Irb_Ma_Trend" indicator review
(https://theindicatorlab.com/reviews/rob-hoffman-irb-ma-trend/): a
3-moving-average ribbon (fast/mid/slow, default ratio ~1:2:4, e.g.
8/16/32) paired with a MACD-derived momentum filter keeps traders out of
choppy false crossovers. Source's own disclosed entry rule: "Ribbon flips
bullish (short MA crosses above the longer MA) and momentum color
confirms (green). Wait for both. If the ribbon flips but momentum stays
neutral, skip it." Operationalized here as: fast SMA crosses above slow
SMA (ribbon flip) AND the standard MACD(12,26,9) histogram is positive at
that bar (momentum confirmation), with the mid SMA used only as a
between-fast-and-slow trend-alignment filter (fast > mid > slow required,
matching the ribbon's "stacked" visual state the source describes as
holding "a consistent color through the middle of the move"). This is
distinct from every other multi-MA construction already in this repo:
GMMA (12-EMA two-cluster ribbon, no momentum filter), TEMA pullback
(single fast/slow TEMA pair, no MACD gate), and Rainbow MA (recursive
SMA cascade, no MACD gate) -- none combine a 3-line ribbon crossover with
an explicit MACD-histogram confirmation gate.

Signal logic
------------
- fast_ma = SMA(close, fast_window) [default 8]
- mid_ma  = SMA(close, mid_window)  [default 16]
- slow_ma = SMA(close, slow_window) [default 32]
- MACD histogram = MACD line (EMA12-EMA26) minus its 9-period signal EMA
  (standard MACD(12,26,9), matching source's "MACD-derived" momentum
  component and its stated "12/26/9 standard MACD works fine" setting).
- Entry (long): fresh crossover of fast_ma above slow_ma (ribbon flip)
  AND fast_ma > mid_ma > slow_ma (stacked/aligned ribbon) AND MACD
  histogram > 0 at that bar (momentum confirms).
- Exit: fast_ma crosses back below slow_ma, OR MACD histogram turns
  negative while in position (momentum fades -- source's "flips right as
  momentum fades" exit cue), OR a max_hold_days time-stop.
- Flat otherwise; long-only.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _macd_histogram(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line - signal_line


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 8,
    mid_window: int = 16,
    slow_window: int = 32,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_ma = close.rolling(fast_window).mean()
    mid_ma = close.rolling(mid_window).mean()
    slow_ma = close.rolling(slow_window).mean()
    hist = _macd_histogram(close, macd_fast, macd_slow, macd_signal)

    fast_above_slow = fast_ma > slow_ma
    ribbon_flip_up = fast_above_slow & (~fast_above_slow.shift(1).fillna(False))
    ribbon_flip_down = (~fast_above_slow) & (fast_above_slow.shift(1).fillna(False))
    stacked = (fast_ma > mid_ma) & (mid_ma > slow_ma)
    momentum_ok = hist > 0

    entry = ribbon_flip_up & stacked & momentum_ok.fillna(False)
    exit_ribbon = ribbon_flip_down
    exit_momentum = ~momentum_ok.fillna(True)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_ribbon.iloc[i]) or bool(exit_momentum.iloc[i]) or held >= max_hold_days:
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
    """Position-weighted daily returns (no transaction costs).

    ``leverage_cap`` (default 1.0) scales notional exposure -- e.g. 0.6
    caps crypto exposure at 60% notional to bring max_drawdown under
    threshold (per this repo's established leverage-cap rescue pattern,
    e.g. 2026-09-18-052/058), without altering generate_signals' binary
    long/flat contract.
    """
    leverage_cap = kwargs.pop("leverage_cap", 1.0)
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret * leverage_cap
    return strategy_ret
