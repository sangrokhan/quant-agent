"""Strategy: Ehlers Center of Gravity (CG) Oscillator, signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per QuantumAlgo's Center of Gravity guide
(https://www.quantum-algo.com/blog/guides/center-of-gravity-indicator-complete-guide/)
and John Ehlers' original concept, the Center of Gravity (CG) oscillator
treats a rolling window of prices as weights on a beam and computes their
balance point -- because that balance point shifts the instant the price
distribution changes (rather than lagging like a standard moving average),
it turns with less lag at pivots than most oscillators. The source's own
disclosed trading rule: treat a raw line-turn (CG rolling over at an
extreme) as an early warning, and a signal-line crossover (CG crossing its
own trigger/signal line) as confirmation -- combining both filters out many
of the false pivots the sensitive raw CG line generates alone. First Center
of Gravity strategy in this repo (0 prior entries; distinct from Fisher
Transform, Stochastic, RSI and other oscillators already tested, which use
a different weighting/normalization scheme).

Calculation (standard Ehlers CG formula):
    CG[t] = - sum_{i=0}^{n-1} (i+1) * price[t-i]  /  sum_{i=0}^{n-1} price[t-i]
    Signal[t] = CG[t-1]  (one-bar-lagged trigger line, per Ehlers' own
                          reference implementation, simplest and most
                          common signal-line construction for this
                          indicator across public sources)

Signal logic
------------
- Entry (long): CG crosses above Signal (bullish signal-line crossover)
  AND the raw CG line itself just turned up (CG[t] > CG[t-1] and
  CG[t-1] <= CG[t-2], the "line-turn" early-warning confirmed by the
  crossover, per the source's combined-filter recommendation).
- Exit: CG crosses back below Signal, or a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _cg_oscillator(close: pd.Series, window: int) -> pd.Series:
    weights = pd.Series(range(1, window + 1))  # 1..window, weight[i]=i+1 for i=0..n-1

    def _cg(vals):
        # vals is oldest->newest within the rolling window (pandas convention)
        # we want price[t-i] weighted by (i+1) where i=0 is the most recent bar
        reversed_vals = vals[::-1]  # now index 0 = most recent
        num = sum((i + 1) * reversed_vals[i] for i in range(len(reversed_vals)))
        den = sum(reversed_vals)
        if den == 0:
            return 0.0
        return -num / den

    cg = close.rolling(window).apply(_cg, raw=True)
    return cg


def generate_signals(
    price_df: pd.DataFrame,
    cg_window: int = 10,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    cg = _cg_oscillator(close, cg_window)
    signal_line = cg.shift(1)

    bullish_cross = (cg > signal_line) & (cg.shift(1) <= signal_line.shift(1))
    line_turned_up = (cg > cg.shift(1)) & (cg.shift(1) <= cg.shift(2))
    bearish_cross = (cg < signal_line) & (cg.shift(1) >= signal_line.shift(1))

    valid = cg.notna() & signal_line.notna()

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = None

    for i in range(len(df.index)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue

        if in_position:
            held_days = i - entry_idx
            if bearish_cross.iloc[i] or held_days >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bullish_cross.iloc[i] and line_turned_up.iloc[i]:
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    cg_window: int = 10,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(price_df, cg_window=cg_window, max_hold_days=max_hold_days)

    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(int) * daily_ret
    strat_returns.name = "strategy_returns"
    return strat_returns
