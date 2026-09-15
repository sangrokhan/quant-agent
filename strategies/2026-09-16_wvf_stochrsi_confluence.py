"""Strategy: Williams VIX Fix (WVF) capitulation spike + Stochastic RSI
oversold confirmation confluence, mean-reversion long entry.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Per Google AI-overview summary of TradingView/agenticks.ca community
writeups on combining "Williams VIX Fix" with a momentum-oscillator
confirmation (read via browser_exec fallback this iteration -- web_search's
DDGS backend failed with a Yahoo/TLS connection error on the first query):
WVF = 100 * (Highest(Close, wvf_window) - Low) / Highest(Close, wvf_window),
a synthetic instrument-agnostic VIX-style panic/capitulation proxy (Larry
Williams). The source's disclosed confluence rule is: (1) wait for WVF to
spike above its own rolling upper Bollinger Band (wvf_bb_window, wvf_bb_std)
-- a volatility/panic spike -- AND (2) require a momentum-oscillator
confirmation that the underlying is genuinely oversold, specifically
Stochastic RSI %K below an oversold threshold (default 20) -- before
entering long, only after the trigger bar closes (avoid intraday false
breakouts). Exit when the confirmation oscillator (Stochastic RSI %K)
crosses back above an overbought threshold (default 80), or a max_hold_days
time-stop backstop if neither extreme is reached.

This repo has 2 prior standalone Williwilliams VIX Fix entries
(2026-09-06-115: WVF spike above its own Bollinger upper band, standalone,
REJECTED -- SPY/QQQ Sharpe or param-sensitivity fail, crypto 0/48;
2026-09-10-099: WVF PercentRank(10) > 98th percentile, standalone with a
next-up-day exit, ACCEPTED QQQ only). This iteration is distinct from both:
it requires WVF's Bollinger-band spike (the *first* prior entry's trigger,
which alone failed) AND adds a second, independent oscillator-based
confirmation gate (Stochastic RSI oversold) plus a symmetric
oscillator-crossover exit (rather than the first entry's fixed Bollinger
midline-reversion exit or the second entry's next-up-day exit) -- testing
whether the earlier standalone WVF-Bollinger rejection was a
false-positive-rate problem (too many spikes without genuine oversold
confirmation) that a second, independent oscillator gate fixes.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _wvf(close: pd.Series, low: pd.Series, wvf_window: int = 22) -> pd.Series:
    """Williams VIX Fix: 100 * (Highest(Close, N) - Low) / Highest(Close, N)."""
    highest_close = close.rolling(wvf_window).max()
    wvf = 100.0 * (highest_close - low) / highest_close
    return wvf


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def _stoch_rsi(close: pd.Series, rsi_window: int = 14, stoch_window: int = 14) -> pd.Series:
    """Stochastic RSI %K: (RSI - min(RSI, N)) / (max(RSI, N) - min(RSI, N)) * 100."""
    rsi = _rsi(close, window=rsi_window)
    lo = rsi.rolling(stoch_window).min()
    hi = rsi.rolling(stoch_window).max()
    rng = (hi - lo).replace(0, np.nan)
    stoch_k = 100.0 * (rsi - lo) / rng
    return stoch_k.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    wvf_window: int = 22,
    wvf_bb_window: int = 20,
    wvf_bb_std: float = 2.0,
    stoch_rsi_window: int = 14,
    stoch_stoch_window: int = 14,
    oversold_threshold: float = 20.0,
    overbought_threshold: float = 80.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """0/1 long-only position series.

    Entry: WVF closes above its own rolling Bollinger upper band (panic
    spike) AND Stochastic RSI %K is below `oversold_threshold` on the same
    bar (confirmation of genuine oversold conditions), entered on the NEXT
    bar's open equivalent (i.e. signal shifted, matching other strategies'
    prior-day-signal convention applied inside generate_returns).
    Exit: Stochastic RSI %K crosses back above `overbought_threshold`, or
    `max_hold_days` bars have elapsed since entry, whichever comes first.
    """
    df = _prep(price_df)
    close = df["close"]
    low = df["low"] if "low" in df.columns else close

    wvf = _wvf(close, low, wvf_window=wvf_window)
    wvf_mid = wvf.rolling(wvf_bb_window).mean()
    wvf_std = wvf.rolling(wvf_bb_window).std()
    wvf_upper = wvf_mid + wvf_bb_std * wvf_std

    stoch_k = _stoch_rsi(close, rsi_window=stoch_rsi_window, stoch_window=stoch_stoch_window)

    entry_trigger = (wvf > wvf_upper) & (stoch_k < oversold_threshold)
    exit_trigger = stoch_k > overbought_threshold

    entry_trigger = entry_trigger.fillna(False).to_numpy()
    exit_trigger = exit_trigger.fillna(False).to_numpy()

    n = len(close)
    position = np.zeros(n)
    in_pos = False
    bars_held = 0
    for i in range(n):
        if in_pos:
            bars_held += 1
            if exit_trigger[i] or bars_held >= max_hold_days:
                in_pos = False
                bars_held = 0
            else:
                position[i] = 1.0
        else:
            if entry_trigger[i]:
                in_pos = True
                bars_held = 0
                position[i] = 1.0

    return pd.Series(position, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    wvf_window: int = 22,
    wvf_bb_window: int = 20,
    wvf_bb_std: float = 2.0,
    stoch_rsi_window: int = 14,
    stoch_stoch_window: int = 14,
    oversold_threshold: float = 20.0,
    overbought_threshold: float = 80.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        wvf_window=wvf_window,
        wvf_bb_window=wvf_bb_window,
        wvf_bb_std=wvf_bb_std,
        stoch_rsi_window=stoch_rsi_window,
        stoch_stoch_window=stoch_stoch_window,
        oversold_threshold=oversold_threshold,
        overbought_threshold=overbought_threshold,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
