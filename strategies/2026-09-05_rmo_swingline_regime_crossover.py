"""Strategy: Rahul Mohindar Oscillator (RMO) swing-line crossover, gated by
the RMO zero-line trend-regime bias.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-004):
The Rahul Mohindar Oscillator (Viratech India, official MetaStock 10
inclusion 2006) builds a long-term trend-bias line from a chain of 10
successively-smoothed SMAs applied to the closing price (RMO = Close - the
10th-order smoothed SMA), then derives two faster swing/timing lines by
EMA-smoothing the RMO line itself. Per trendsandbreakouts.com's RMO guide,
the mechanical trading rule is two-layered: (1) the RMO line's sign vs zero
defines the long-term regime (positive=bullish, negative=bearish), and (2)
within that regime, the medium-term swing line (ST2) crossing above the
slower swing line (ST3) is the entry-timing trigger -- the crossover
"matters more when it happens on the correct side of the zero line" per the
source. Exit on the reverse ST2/ST3 crossover or the RMO regime flipping
negative. First Rahul Mohindar Oscillator strategy in this repo -- distinct
from other chained/multi-stage smoothing constructions already tested
(GMMA's 12-EMA ribbon, FRAMA's fractal-adaptive single EMA) since RMO's
core bias line is a *difference* (Close minus a 10th-order SMA chain), not
a ribbon or adaptive-alpha average.

Signal logic
------------
- MA_1 = SMA(close, sma_period); MA_k = SMA(MA_{k-1}, sma_period) for
  k=2..10 (10 chained SMAs, per the source's own formula).
- RMO = close - MA_10  (long-term trend-bias line).
- ST2 = EMA(RMO, st2_span); ST3 = EMA(ST2, st3_span) (medium/slow swing
  timing lines).
- Entry (long): ST2 crosses above ST3 AND RMO > 0 (bullish regime).
- Exit: ST2 crosses below ST3, OR RMO drops <= 0 (regime flip), OR a
  max_hold_days time-stop backstop.
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


def _rmo(close: pd.Series, sma_period: int, st2_span: int, st3_span: int):
    ma = close
    for _ in range(10):
        ma = ma.rolling(sma_period, min_periods=max(2, sma_period // 2)).mean()
    rmo = close - ma
    st2 = rmo.ewm(span=st2_span, adjust=False).mean()
    st3 = st2.ewm(span=st3_span, adjust=False).mean()
    return rmo, st2, st3


def generate_signals(
    price_df: pd.DataFrame,
    sma_period: int = 2,
    st2_span: int = 30,
    st3_span: int = 30,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rmo, st2, st3 = _rmo(close, sma_period, st2_span, st3_span)

    st2_above = st2 > st3
    entry_cross = st2_above & (~st2_above.shift(1).fillna(False))
    bullish_regime = rmo > 0

    entry = entry_cross & bullish_regime.fillna(False)
    exit_signal = (~st2_above) | (~bullish_regime.fillna(False))

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
