"""Strategy: Ehlers Cyber Cycle / Trigger-line crossover, trend-filtered.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per TradingView's "[blackcat] L2 Ehlers Cyber Cycle Trading Strategy" page
(https://in.tradingview.com/scripts/cybercycle/, itself summarizing John
Ehlers' "Cybernetic Analysis for Stocks and Futures" Ch.4, 2004): the Cyber
Cycle is a 2-pole high-pass-filtered, 4-bar-smoothed oscillator designed to
isolate the market's dominant short-term cycle while rejecting trend/noise:

    Smooth[i] = (Price[i] + 2*Price[i-1] + 2*Price[i-2] + Price[i-3]) / 6
    Cycle[i]  = (1 - 0.5*alpha)^2 * (Smooth[i] - 2*Smooth[i-1] + Smooth[i-2])
                + 2*(1-alpha)*Cycle[i-1] - (1-alpha)^2*Cycle[i-2]

with Price = (High+Low)/2 and alpha the standard Ehlers smoothing
coefficient (default 0.07, ~1-cycle-per-14-bar dominant period). The
"Trigger" line is the Cycle delayed by one bar (Cycle.shift(1)); a
bullish crossover (Cycle crosses above Trigger) signals a cyclic upturn.

The source explicitly warns raw Cycle/Trigger crossovers carry several
bars of lag and can be "exactly wrong" in a strongly trending market
(the escape mechanism it describes is to reverse position if held too
long at a loss). Rather than reproduce that reversal-on-loss escape hatch
(out of scope/too close to a stop-loss mechanic already covered elsewhere
in this repo), we take the more conservative, testable adaptation used
elsewhere in this repo for lag-prone oscillators: gate the raw Cycle >
Trigger bullish crossover with a trend_window-day SMA trend filter (only
trade cyclic upturns in an already-favorable broader trend, avoiding the
"lag makes the signal wrong in a strong trend" failure mode the source
itself flags), with a max_hold_days time-stop exit backstop.

First Ehlers Cyber Cycle entry in this repo (zero prior "Cyber Cycle"/
"CyberCycle" matches in strategies_index.jsonl) -- distinct from other
Ehlers-family entries already tested (FRAMA, MAMA/FAMA, Fisher Transform,
Sinewave) since Cyber Cycle's specific construction is a 2-pole
high-pass filter + 4-bar FIR smoother, not an adaptive moving average or
inverse-Fisher transform.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Position-weighted daily strategy returns (no transaction costs).
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} long/flat position series aligned to price_df.index.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _cyber_cycle(price: pd.Series, alpha: float) -> pd.Series:
    n = len(price)
    smooth = pd.Series(index=price.index, dtype=float)
    cycle = pd.Series(0.0, index=price.index, dtype=float)

    p = price.values
    sm = [0.0] * n
    cy = [0.0] * n
    for i in range(n):
        if i >= 3:
            sm[i] = (p[i] + 2 * p[i - 1] + 2 * p[i - 2] + p[i - 3]) / 6.0
        else:
            sm[i] = p[i]

        if i >= 4:
            cy[i] = (
                (1 - 0.5 * alpha) ** 2 * (sm[i] - 2 * sm[i - 1] + sm[i - 2])
                + 2 * (1 - alpha) * cy[i - 1]
                - (1 - alpha) ** 2 * cy[i - 2]
            )
        else:
            cy[i] = (p[i] - 2 * p[i - 1] + p[i - 2]) / 4.0 if i >= 2 else 0.0

    smooth[:] = sm
    cycle[:] = cy
    return cycle


def generate_signals(
    price_df: pd.DataFrame,
    alpha: float = 0.07,
    trend_window: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    typical_price = (high + low) / 2.0

    cycle = _cyber_cycle(typical_price, alpha)
    trigger = cycle.shift(1)

    sma_trend = close.rolling(trend_window).mean()

    bullish_cross = (cycle > trigger) & (cycle.shift(1) <= trigger.shift(1))
    bearish_cross = (cycle < trigger) & (cycle.shift(1) >= trigger.shift(1))

    entry = bullish_cross & (close > sma_trend)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    valid_start = sma_trend.first_valid_index()
    # cycle needs at least ~5 bars of warmup too
    warmup_idx = close.index[min(6, len(close) - 1)] if len(close) > 6 else None
    if valid_start is not None and warmup_idx is not None:
        valid_start = max(valid_start, warmup_idx)

    for i in range(len(close)):
        if valid_start is not None and close.index[i] < valid_start:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(bearish_cross.iloc[i]) or held >= max_hold_days:
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
