"""Strategy: Mass Index (Donald Dorsey) "reversal bulge" counter-trend signal.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per stockcharts.com ChartSchool's "Mass Index" page (visited this iteration
via browser_exec, web_search DDGS backend TLS-connection-errored on the
query) and corroborating Google SERP snippets (Investopedia, TradingView,
TradingSim, GU Analyser, Definedge -- all describing the identical
mechanical rule): the Mass Index is a DIRECTIONLESS volatility indicator
built from the high-low range: Single EMA = EMA(high-low, ema_period);
Double EMA = EMA(Single EMA, ema_period); EMA Ratio = Single EMA / Double
EMA; Mass Index = rolling sum of the EMA Ratio over sum_period bars
(defaults: ema_period=9, sum_period=25). Donald Dorsey's disclosed
"reversal bulge" signal fires when the Mass Index rises above
bulge_threshold (default 27) and SUBSEQUENTLY falls back below
reset_threshold (default 26.5) -- because the index has no directional
bias, Dorsey's own rule (confirmed across every source above) is to use
the PRIOR trend to set direction: a reversal bulge completing during a
downtrend suggests a bullish reversal is imminent; a reversal bulge
completing during an uptrend suggests a bearish reversal. This is a
long-only implementation: go long when a reversal bulge completes while
price was in a downtrend (below its trend_sma), and exit to flat when a
reversal bulge completes while price was in an uptrend (above its
trend_sma) -- Dorsey's own directional overlay rule, not an invented one.

Distinct from every other volatility/regime-based strategy already in this
repo: Mass Index measures range EXPANSION VELOCITY via a ratio of two
differently-lagged EMAs of the high-low range (not realized-vol terciles,
ATR level, or Bollinger-band width), and its signal is a bulge-then-reset
PATTERN rather than a simple threshold crossing. 0 prior Mass Index entries
in this repo.

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


def _mass_index(high: pd.Series, low: pd.Series, ema_period: int, sum_period: int) -> pd.Series:
    hl_range = (high - low).abs()
    single_ema = hl_range.ewm(span=ema_period, adjust=False).mean()
    double_ema = single_ema.ewm(span=ema_period, adjust=False).mean()
    ratio = single_ema / double_ema.replace(0, pd.NA)
    return ratio.rolling(sum_period).sum()


def generate_signals(
    price_df: pd.DataFrame,
    ema_period: int = 9,
    sum_period: int = 25,
    bulge_threshold: float = 27.0,
    reset_threshold: float = 26.5,
    trend_sma: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: a "reversal bulge" completes (Mass Index rose above
    bulge_threshold at some point, then falls back below reset_threshold)
    while price was BELOW its trend_sma (prior downtrend) -- Dorsey's own
    rule: downtrend + reversal bulge => expect bullish reversal.
    Exit to flat: a reversal bulge completes while price was ABOVE its
    trend_sma (prior uptrend) -- expect bearish reversal.
    Holds its last state between signals (there is no separate stop rule
    disclosed by the source; this measures how long a bullish reversal call
    persists until the opposite-direction bulge, if any, fires).
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    mi = _mass_index(high, low, ema_period=ema_period, sum_period=sum_period)
    sma = close.rolling(trend_sma).mean()
    downtrend = close < sma
    uptrend = close >= sma

    bulge_active = False
    position = pd.Series(0, index=close.index, dtype=int)
    state = 0
    mi_vals = mi.values
    down_vals = downtrend.values
    up_vals = uptrend.values

    for i in range(len(close)):
        val = mi_vals[i]
        if pd.isna(val):
            position.iloc[i] = state
            continue
        if not bulge_active:
            if val > bulge_threshold:
                bulge_active = True
        else:
            if val < reset_threshold:
                # Reversal bulge completes here -- apply Dorsey's
                # trend-dependent directional overlay.
                bulge_active = False
                if bool(down_vals[i]):
                    state = 1
                elif bool(up_vals[i]):
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
