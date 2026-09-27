"""Strategy: IBS + rolling-range-band mean reversion with an EXHAUSTION-based
exit (IBS>exit_ibs OR RSI(2)>exit_rsi), instead of this repo's existing
"close > prior day's high" or "close < SMA stop" exits for the same entry
family.

Hypothesis (see knowledge_base/strategies_log.jsonl entry for this
iteration's id): Per Quantitativo's "Murphy's Law: How a fragile mean
reversion idea became a +1.2 Sharpe strategy"
(https://www.quantitativo.com/p/murphys-law, read via browser_exec this
iteration -- web_search DDGS backend returned empty/irrelevant results for
several queries attempted), the article iteratively improves a mean-
reversion strategy and finds that switching the exit rule from a simple
"close > prior day's high" breakout exit to a DYNAMIC EXHAUSTION exit --
close the trade as soon as IBS > 0.9 (closed near the top of its own daily
range, "already bounced") OR RSI(2) > 90 (extremely short-term overbought)
-- meaningfully improves the strategy's expected return per trade (+1.04%
vs +0.90% with the plain breakout exit, source's own disclosed numbers,
statistically significant t-stat=5.37, p=0.0). The source's underlying
entry logic itself (a statistically significant price drop + low IBS,
gated by a 200-day trend filter) is already extensively tested in this
repo (e.g. 2026-09-09-041, 2026-09-08-133) using EITHER a plain breakout
exit OR a dynamic SMA-stop exit -- neither of which is this specific
"IBS>0.9 OR RSI(2)>90 exhaustion" exit. This iteration isolates that one
exit-logic change on top of this repo's existing accepted entry
construction (rolling-high-anchored range band + low IBS + 200d SMA
uptrend gate) to test whether the source's own finding (a smarter exit
beats a fixed breakout exit) replicates on QQQ/SPY/BTC/USDT/ETH/USDT daily
bars.

Signal logic
------------
- avg_range = rolling mean of (High-Low), band_window periods.
- rolling_high = rolling max of High, band_window periods.
- lower_band = rolling_high - band_mult * avg_range.
- IBS = (Close-Low)/(High-Low).
- RSI2 = 2-period Wilder RSI of Close.
- Entry (long) at close when: close < lower_band AND IBS < entry_ibs AND
  close > SMA(trend_window) (200d uptrend gate, per this repo's
  established convention for this entry family).
- Exit (flat) at close when: IBS > exit_ibs OR RSI2 > exit_rsi.
- max_hold_days safety valve (source's article uses walk-forward analysis
  over many trades; this repo's convention always bounds worst-case
  holding period since the source's own exhaustion exit could in
  principle never fire).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    band_window: int = 25,
    band_mult: float = 2.5,
    entry_ibs: float = 0.3,
    exit_ibs: float = 0.9,
    exit_rsi: float = 90.0,
    rsi_period: int = 2,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    avg_range = (high - low).rolling(band_window).mean()
    rolling_high = high.rolling(band_window).max()
    lower_band = rolling_high - band_mult * avg_range

    hl_range = (high - low).replace(0, pd.NA)
    ibs = ((close - low) / hl_range).fillna(0.5)

    rsi2 = _rsi(close, rsi_period)
    sma_trend = close.rolling(trend_window).mean()

    entry = (close < lower_band) & (ibs < entry_ibs) & (close > sma_trend)
    exit_signal = (ibs > exit_ibs) | (rsi2 > exit_rsi)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) if pd.notna(entry.iloc[i]) else False:
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
    strategy_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strategy_ret
