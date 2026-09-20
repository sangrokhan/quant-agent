"""Strategy: Stochastic Momentum Index (William Blau) signal-line crossover
from oversold territory, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Google SERP corroboration this iteration (browser_exec fallback --
web_search DDGS backend TLS-connection-errored on the query):
tradiecapital.com, XBTFX, LuxAlgo, heywarren.com, and LizardIndicators all
describe the identical mechanical rule for William Blau's 1993 Stochastic
Momentum Index (SMI): SMI measures the distance of the close from the
MIDPOINT of the high/low range (not the low, as in the classic Stochastic
Oscillator), double-EMA-smoothed, and scaled to oscillate between -100 and
+100. The disclosed trading rule (XBTFX, LuxAlgo, heywarren.com,
LizardIndicators, all corroborating): watch for SMI/signal-line (typically
a 3-period EMA of SMI) crossovers that emerge FROM oversold/overbought
territory (commonly +/-40, though some sources use +/-50) rather than
mid-range crossovers -- i.e. go long when SMI crosses above its signal
line while SMI was recently in oversold territory (<= -oversold_threshold).

Formula (Blau's standard construction):
    midpoint_range = (Highest High(n) + Lowest Low(n)) / 2
    delta = Close - midpoint_range
    high_low_range = Highest High(n) - Lowest Low(n)
    smoothed_delta = EMA(EMA(delta, ema1), ema2)
    smoothed_range = EMA(EMA(high_low_range, ema1), ema2)
    SMI = 100 * smoothed_delta / (smoothed_range / 2)
    signal = EMA(SMI, signal_period)

Distinct from every other stochastic/oscillator strategy in this repo:
SMI measures distance from the RANGE MIDPOINT (not the range low, as the
classic %K stochastic does), with a DOUBLE EMA smoothing pass -- a
genuinely different construction from plain Stochastic %K/%D, RSI, or
Williams %R already tested. 0 prior Blau SMI entries in this repo.

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


def _smi(high: pd.Series, low: pd.Series, close: pd.Series, n: int, ema1: int, ema2: int, signal_period: int):
    highest_high = high.rolling(n).max()
    lowest_low = low.rolling(n).min()
    midpoint = (highest_high + lowest_low) / 2.0
    delta = close - midpoint
    hl_range = highest_high - lowest_low

    smoothed_delta = delta.ewm(span=ema1, adjust=False).mean().ewm(span=ema2, adjust=False).mean()
    smoothed_range = hl_range.ewm(span=ema1, adjust=False).mean().ewm(span=ema2, adjust=False).mean()

    smi = 100 * smoothed_delta / (smoothed_range / 2.0).replace(0, pd.NA)
    signal = smi.ewm(span=signal_period, adjust=False).mean()
    return smi, signal


def generate_signals(
    price_df: pd.DataFrame,
    n: int = 13,
    ema1: int = 25,
    ema2: int = 2,
    signal_period: int = 3,
    oversold_threshold: float = 40.0,
    lookback_for_oversold: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: SMI crosses above its signal line AND SMI dipped to/below
    -oversold_threshold at some point in the trailing `lookback_for_oversold`
    bars (the disclosed "crossover emerging from oversold territory" rule).
    Exit to flat: SMI crosses below its signal line while in/near
    overbought territory (>= +oversold_threshold at some point in the same
    trailing window) -- the mirror-image disclosed rule; otherwise holds.
    """
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    smi, signal = _smi(high, low, close, n=n, ema1=ema1, ema2=ema2, signal_period=signal_period)

    cross_up = (smi > signal) & (smi.shift(1) <= signal.shift(1))
    cross_down = (smi < signal) & (smi.shift(1) >= signal.shift(1))

    was_oversold = (smi.rolling(lookback_for_oversold).min() <= -oversold_threshold)
    was_overbought = (smi.rolling(lookback_for_oversold).max() >= oversold_threshold)

    long_signal = cross_up & was_oversold
    exit_signal = cross_down & was_overbought

    n_bars = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    state = 0
    long_vals = long_signal.fillna(False).values
    exit_vals = exit_signal.fillna(False).values

    for i in range(n_bars):
        if bool(long_vals[i]):
            state = 1
        elif bool(exit_vals[i]):
            state = 0
        position.iloc[i] = state

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
