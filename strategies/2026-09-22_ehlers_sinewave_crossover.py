"""Strategy: Ehlers Sine Wave indicator two-line crossover (Sine vs LeadSine).

Hypothesis (see knowledge_base/strategies_log.jsonl for this id):
John Ehlers' Sine Wave indicator (Rocket Science For Traders, ch. on cycle
measurement) uses the Hilbert Transform to estimate the dominant market
cycle period and phase, then projects a Sine line and a "LeadSine" line
(sine of phase+45deg, i.e. a lead of 1/8 cycle). Per NinjaTrader Ecosystem's
own stated rule ("Buy when the blue [Sine] line crosses over the red
[LeadSine] line") and Stonehill Forex's confirmation-indicator writeup
("Green [faster] crosses above Gold [slower] = LONG confirmation"), a
crossover of Sine above LeadSine signals the market is entering an
up-swing of its dominant cycle, and is used as a mechanical long entry;
the reverse crossover (Sine crosses below LeadSine) signals the down-swing
and is used as the exit/flat signal. This repo has 0 prior "Sine Wave"
entries -- first Ehlers Hilbert-Transform cycle-phase strategy tested here
(distinct from the repo's existing MESA/Roofing-Filter/Instantaneous-
Trendline/Adaptive-Cyber-Cycle Ehlers-family entries, none of which use
the Sine/LeadSine two-line phase-cross construction).

Sources:
- https://ninjatraderecosystem.com/the-sine-wave-indicator/ (page returned
  404 for this specific slug when fetched this iteration via browser_exec;
  disclosed rule captured from Google SERP snippet: "Buy when the blue
  line crosses over the red [line]" -- John Ehlers, Cybernetic Analysis
  For Stocks And Futures pgs 154-155)
- https://stonehillforex.com/2026/08/ehlers-sine-wave-stochastic-as-a-confirmation-indicator/
  (read via browser_exec this iteration; disclosed rule: "Green Crosses
  Above Gold = LONG Confirmation" / "Green Crosses Below Gold = SHORT
  Confirmation" for the faster/slower Sine-family line pair)

Because a true Hilbert-Transform dominant-cycle-period estimator is
involved and heavier than this repo's simplified toolkit typically
implements, this version approximates the Sine/LeadSine phase estimate
using a fixed-period assumption (the classic Ehlers simplification when
the adaptive period estimator is not available): phase is derived from a
band-pass-filtered price series' arctangent, using a fixed
`cycle_period` parameter (tunable, default 20 per Ehlers' typical
starting point for daily equity/crypto data) rather than the full
adaptive MESA period estimate -- this is a standard, disclosed
simplification of the source's own indicator when only a fixed period is
assumed instead of dynamically measured.

Signal logic
------------
- Detrend price using a simple high-pass filter (price minus its own
  `cycle_period`-length SMA) to isolate cycle behavior from trend.
- Estimate instantaneous phase via arctangent of a quadrature pair built
  from the detrended series at lag `cycle_period/4` (quarter-cycle lag
  approximates the Hilbert quadrature component for a fixed-period cycle).
- Sine = sin(phase); LeadSine = sin(phase + 45 degrees).
- Entry (long): Sine crosses above LeadSine.
- Exit (flat): Sine crosses below LeadSine.
- Optional `trend_window` SMA uptrend gate (close > SMA(trend_window)) may
  be combined to filter to trending-favorable regimes, per this repo's
  standard practice; trend_window=0 disables the gate.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _sine_leadsine(close: pd.Series, cycle_period: int) -> tuple[pd.Series, pd.Series]:
    """Approximate Ehlers Sine/LeadSine using a fixed-period quadrature estimate."""
    hp = close - close.rolling(cycle_period).mean()
    quarter_lag = max(1, cycle_period // 4)
    # Quadrature component: quarter-cycle-lagged version of the detrended
    # series (standard fixed-period approximation of the Hilbert
    # Transform's 90-degree phase shift).
    quad = hp.shift(quarter_lag)
    # Normalize both components to avoid amplitude bias in the arctangent.
    hp_std = hp.rolling(cycle_period).std().replace(0, np.nan)
    in_phase = (hp / hp_std).clip(-3, 3)
    quad_phase = (quad / hp_std).clip(-3, 3)
    phase = np.arctan2(quad_phase, in_phase)
    sine = np.sin(phase)
    lead_sine = np.sin(phase + np.pi / 4)
    return pd.Series(sine, index=close.index), pd.Series(lead_sine, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    cycle_period: int = 20,
    trend_window: int = 0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sine, lead_sine = _sine_leadsine(close, cycle_period)

    cross_up = (sine > lead_sine) & (sine.shift(1) <= lead_sine.shift(1))
    cross_down = (sine < lead_sine) & (sine.shift(1) >= lead_sine.shift(1))

    if trend_window and trend_window > 0:
        trend_ok = close > close.rolling(trend_window).mean()
    else:
        trend_ok = pd.Series(True, index=close.index)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(cross_down.iloc[i]) or not bool(trend_ok.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]) and bool(trend_ok.iloc[i]):
                in_position = True
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
