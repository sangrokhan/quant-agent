"""Strategy: Rainbow Moving Average cascade stacking + widening-separation trend.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-070):
The Rainbow Moving Average is a cascade of ~10 same-type SMAs where each
layer is an SMA of the PRECEDING layer (not independent periods on raw price
like GMMA). Per quantifiedstrategies.com's Rainbow Moving Average article
(no numeric backtest published there -- "A backtested strategy is coming
shortly" -- so this hypothesis mechanically operationalizes the page's own
qualitative description): "When the early layer (shorter-period) MAs stay
above the subsequent layer (longer-period) MAs and keep rising further away
from the latter, the market is in an uptrend ... The farther away the
primary SMA is from the last ones, the stronger the trend, while the closer
they are together, the weaker the trend." Long entry when ALL layers are
in fully-stacked bullish order (layer1 > layer2 > ... > layerN) AND the
top-minus-bottom-layer spread (normalized by price) is expanding vs its own
recent average; exit when the stacking order breaks (any layer inversion)
or a max_hold_days time-stop.

Distinct from Guppy Multiple Moving Average (2026-09-04-062, rejected):
GMMA uses two independent clusters of EMAs on raw price with different fixed
periods each; Rainbow MA is a single SMA-of-SMA recursive cascade (each
layer literally smooths the prior layer, not the raw price), a structurally
different construction and this test uses a full-stack ordering + expanding
spread trigger rather than GMMA's cluster-average-crossover trigger.

Signal logic
------------
- Build `n_layers` layers: layer[0] = SMA(close, window); layer[k] =
  SMA(layer[k-1], window) for k = 1..n_layers-1.
- Fully-stacked bullish state: layer[0] > layer[1] > ... > layer[n_layers-1]
  on the same bar.
- Spread = (layer[0] - layer[-1]) / close; spread_expanding = spread >
  spread.rolling(spread_lookback).mean().
- Entry (long): fully-stacked bullish AND spread_expanding.
- Exit: stacking order breaks (not fully-stacked bullish anymore), OR a
  max_hold_days time-stop.

Interface contract (RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rainbow_layers(close: pd.Series, window: int, n_layers: int) -> list[pd.Series]:
    layers = []
    prev = close
    for _ in range(n_layers):
        layer = prev.rolling(window).mean()
        layers.append(layer)
        prev = layer
    return layers


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 5,
    n_layers: int = 8,
    spread_lookback: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    layers = _rainbow_layers(close, window, n_layers)

    fully_stacked_bull = pd.Series(True, index=close.index)
    for k in range(n_layers - 1):
        fully_stacked_bull &= layers[k] > layers[k + 1]

    spread = (layers[0] - layers[-1]) / close
    spread_avg = spread.rolling(spread_lookback).mean()
    spread_expanding = spread > spread_avg

    entry = fully_stacked_bull.fillna(False) & spread_expanding.fillna(False)
    exit_stack_break = ~fully_stacked_bull.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_stack_break.iloc[i]) or held >= max_hold_days:
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
