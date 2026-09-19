"""Strategy: Bitcoin Bollinger-Band dip-buy with trend filter and ATR
trailing stop (fix for the naive mean-reversion-exit version's structural
flaw).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-025):
Per CoinQuant's "Does Buying the Dip Work in Crypto? 9 Years of Backtested
Evidence" (https://www.coinquant.ai/blog/does-buying-the-dip-work-in-crypto-9-years-of-backtested-evidence,
read via browser_exec after web_search returned generic results):
CoinQuant's own disclosed backtest of a naive BTC dip-buy (long when close
crosses below the lower 20-day/2-std Bollinger Band, exit when close
recovers to the middle band/SMA) LOST money (-13.0% total return) over
2020-2026 despite a 63.2% win rate, because the mean-reversion exit
structurally capped winners at the mean while occasional dips-that-turned-
into-downtrends produced large losses, missing BTC's +714.1% buy-and-hold
return entirely. The source's OWN explicitly stated next-step suggestions
(quoted directly): "Filter the dips. Only buy dips when a longer-term
trend is up" and "Let winners run. Replace the mean-reversion exit with a
trailing stop so recoveries that turn into trends are not cut short."

This repo already has a QQQ Bollinger-Band mean-reversion strategy gated
by a VOLATILITY regime filter (2026-09-03_bb_meanrev_qqq_volregime.py,
exits at SMA cross / vol-regime-flip / time-stop), but has never tested
this specific combination: BB dip entry + a longer-term TREND filter
(distinct from a vol-regime filter) + an ATR-based TRAILING stop replacing
the mean-reversion exit -- directly implementing the source's own
diagnosed fix for its own disclosed failed baseline.

Signal logic
------------
- bb_window/bb_std define the entry Bollinger Band (default 20-day, 2std).
- trend_window defines the longer-term trend filter SMA (default 200-day);
  entries only allowed when close > this SMA (only buy dips within an
  established uptrend, per the source's own suggestion).
- Entry (long): close crosses below the lower Bollinger Band AND
  close > SMA(trend_window).
- Exit: an ATR-based trailing stop (atr_window-day ATR, atr_mult
  multiplier) that only ever ratchets upward once in position (never
  loosens), replacing the source's naive fixed mean-reversion exit so
  that a dip which turns into a sustained rally is allowed to run rather
  than being sold at the first touch of the mean; also a max_hold_days
  backstop.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    trend_window: int = 200,
    atr_window: int = 14,
    atr_mult: float = 3.0,
    max_hold_days: int = 90,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    sma_bb = close.rolling(bb_window).mean()
    std_bb = close.rolling(bb_window).std()
    lower_band = sma_bb - bb_std * std_bb

    trend_sma = close.rolling(trend_window).mean()
    trend_ok = close > trend_sma

    atr = _atr(df, atr_window)

    prev_close = close.shift(1)
    prev_lower = lower_band.shift(1)
    cross_below = (prev_close >= prev_lower) & (close < lower_band)

    entry = cross_below & trend_ok.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = None

    for i in range(n):
        if in_position:
            held = i - entry_idx
            current_atr = atr.iloc[i]
            price_now = close.iloc[i]
            if current_atr is not None and current_atr == current_atr:
                candidate_stop = price_now - atr_mult * current_atr
                if stop_level is None:
                    stop_level = candidate_stop
                else:
                    stop_level = max(stop_level, candidate_stop)
            if stop_level is not None and (price_now < stop_level or held >= max_hold_days):
                in_position = False
                position.iloc[i] = 0
                stop_level = None
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                entry_atr = atr.iloc[i]
                if entry_atr is not None and entry_atr == entry_atr:
                    stop_level = close.iloc[i] - atr_mult * entry_atr
                else:
                    stop_level = None
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
