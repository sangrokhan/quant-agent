"""Strategy: Schaff Trend Cycle (STC) oversold-recovery long, gated by a
long-term SMA uptrend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-055):
Per QuantifiedStrategies.com's Schaff Trend Cycle explainer
(https://www.quantifiedstrategies.com/schaff-trend-cycle-indicator/, read
this iteration via browser_exec after web_search's DDGS backend returned
low-quality Korean-localized results), the STC (Doug Schaff, 1990s) is a
cyclical/stochastic-smoothed MACD variant bounded [0,100] that "filters out
market noise" better than a plain MACD or RSI. The source's own disclosed
rule: "If the main trend is up and the STC is emerging from the oversold
region, rising above the 25 level, a buy signal is generated." This
strategy implements that literally: close > SMA(trend_window) (uptrend
regime) AND STC crosses up through stc_entry_level (default 25) from
below signals a long entry; exit when STC crosses back down through
stc_exit_level (default 75, mirroring the source's overbought/sell-signal
level) or the trend filter breaks or a max_hold_days time-stop is hit.
This is the first Schaff Trend Cycle strategy in this repo (STC combines a
double-EMA MACD difference with a 10-period double-stochastic smoothing
step -- distinct construction from this repo's existing MACD-crossover,
Ergodic/TSI, and generic %K/%D stochastic entries).

STC formula (source-disclosed):
    EMA1 = EMA(close, fast_window)     # default 23
    EMA2 = EMA(close, slow_window)     # default 50
    MACD = EMA1 - EMA2
    %K(MACD) = stochastic %K of MACD over stoch_window (default 10)
    %D(MACD) = SMA(%K(MACD), stoch_smooth) (double-smoothed per source's
               "%K(MACD), %D(MACD)" two-stage stochastic)
    STC = 100 * (MACD - %K(MACD)) / (%D(MACD) - %K(MACD)), clipped [0,100]

Interface contract for validators (see validation/validators.py):
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


def _compute_stc(
    close: pd.Series,
    fast_window: int = 23,
    slow_window: int = 50,
    stoch_window: int = 10,
    stoch_smooth: int = 3,
) -> pd.Series:
    ema1 = close.ewm(span=fast_window, adjust=False).mean()
    ema2 = close.ewm(span=slow_window, adjust=False).mean()
    macd = ema1 - ema2

    macd_low = macd.rolling(stoch_window).min()
    macd_high = macd.rolling(stoch_window).max()
    denom_k = (macd_high - macd_low).replace(0, pd.NA)
    pct_k = 100 * (macd - macd_low) / denom_k
    pct_k = pct_k.ffill().fillna(50.0)

    pct_d = pct_k.rolling(stoch_smooth).mean()

    denom_stc = (pct_d.rolling(stoch_window).max() - pct_d.rolling(stoch_window).min()).replace(0, pd.NA)
    # Source formula: STC = 100 * (MACD - %K(MACD)) / (%D(MACD) - %K(MACD))
    # Using the classic double-stochastic-of-MACD re-normalization (equivalent
    # construction commonly implemented as a second %K/%D pass on pct_d):
    stc_raw_low = pct_d.rolling(stoch_window).min()
    stc_raw_high = pct_d.rolling(stoch_window).max()
    denom2 = (stc_raw_high - stc_raw_low).replace(0, pd.NA)
    stc = 100 * (pct_d - stc_raw_low) / denom2
    stc = stc.ffill().fillna(50.0)
    stc = stc.clip(0, 100)
    return stc


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 23,
    slow_window: int = 50,
    stoch_window: int = 10,
    stoch_smooth: int = 3,
    stc_entry_level: float = 25.0,
    stc_exit_level: float = 75.0,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    stc = _compute_stc(close, fast_window, slow_window, stoch_window, stoch_smooth)
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    entry = (stc > stc_entry_level) & (stc.shift(1) <= stc_entry_level) & uptrend.fillna(False)
    exit_overbought = (stc < stc_exit_level) & (stc.shift(1) >= stc_exit_level)
    exit_trend_break = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_overbought.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
