"""Strategy: Kaufman Adaptive Moving Average (KAMA) trend-following, gated by
an ATR-percent-of-price volatility band.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-181):
Kaufman's Adaptive Moving Average (Perry Kaufman) adjusts its smoothing
constant using an Efficiency Ratio (net directional move / sum of absolute
bar-to-bar moves over a lookback window), hugging price closely during
strong efficient trends and flattening out during noisy/choppy conditions.
Per a Google AI-overview synthesis of a Medium (David Borst) "Kaufman
Adaptive Moving Average and ATR Long Position Strategy" write-up, the source
strategy combines a KAMA trend-following crossover with an ATR-based
volatility filter/exit: only trust the crossover-driven long entry when
recent volatility (ATR as a % of price) is inside a "normal" band -- neither
too calm (choppy/no-trend risk) nor too wild (whipsaw/gap risk) -- and force
an exit if volatility spikes past an upper threshold, even before the KAMA
trend flips. First KAMA strategy in this repo -- distinct from all prior
EMA/SMA/ZLEMA/T3 moving-average crossover strategies since KAMA's smoothing
constant is itself a function of trend efficiency (not a fixed span), and
distinct from prior ATR-based stop strategies (SuperTrend, Chande Kroll,
Elder SafeZone) since ATR is used here as an entry-*gate* on a volatility
band rather than a trailing stop distance.

Signal logic
------------
- KAMA(er_window, fast_sc_period, slow_sc_period): efficiency ratio over
  er_window bars maps a fast (fast_sc_period-based) and slow
  (slow_sc_period-based) smoothing-constant blend, applied recursively
  starting from the first available close.
- ATR(atr_window) as a % of close ("atr_pct").
- Entry (long): close crosses above KAMA AND atr_pct is within
  [atr_min_pct, atr_max_pct] (normal-volatility band, avoids entering into
  either dead-flat chop or an already-blown-out volatility spike).
- Exit: close crosses below KAMA, OR atr_pct rises above atr_exit_pct
  (volatility-spike risk-off exit), OR a max_hold_days time-stop.
- Flat (no position) otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (see validation/grid_test.py) -- both generate_signals and
generate_returns accept the strategy's tunable parameters as keyword
arguments so the grid can sweep them directly.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _kama(close: pd.Series, er_window: int, fast_sc_period: int, slow_sc_period: int) -> pd.Series:
    """Kaufman's Adaptive Moving Average."""
    change = (close - close.shift(er_window)).abs()
    volatility = close.diff().abs().rolling(er_window).sum()
    er = (change / volatility.replace(0.0, pd.NA)).fillna(0.0)

    fast_sc = 2.0 / (fast_sc_period + 1)
    slow_sc = 2.0 / (slow_sc_period + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    kama = pd.Series(index=close.index, dtype=float)
    first_valid = close.first_valid_index()
    if first_valid is None:
        return kama
    start_pos = close.index.get_loc(first_valid)
    kama.iloc[start_pos] = close.iloc[start_pos]
    for i in range(start_pos + 1, len(close)):
        prev = kama.iloc[i - 1]
        if pd.isna(prev):
            kama.iloc[i] = close.iloc[i]
            continue
        sc_i = sc.iloc[i]
        if pd.isna(sc_i):
            sc_i = slow_sc ** 2
        kama.iloc[i] = prev + sc_i * (close.iloc[i] - prev)
    return kama


def _atr(df: pd.DataFrame, atr_window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(atr_window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    er_window: int = 10,
    fast_sc_period: int = 2,
    slow_sc_period: int = 30,
    atr_window: int = 14,
    atr_min_pct: float = 0.005,
    atr_max_pct: float = 0.035,
    atr_exit_pct: float = 0.06,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    kama = _kama(close, er_window, fast_sc_period, slow_sc_period)
    atr = _atr(df, atr_window)
    atr_pct = (atr / close).fillna(0.0)

    above = close > kama
    cross_up = above & ~above.shift(1).fillna(False)
    cross_down = (~above) & above.shift(1).fillna(False)

    vol_ok = (atr_pct >= atr_min_pct) & (atr_pct <= atr_max_pct)
    vol_spike = atr_pct > atr_exit_pct

    entry = cross_up & vol_ok

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or bool(vol_spike.iloc[i]) or held >= max_hold_days:
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
