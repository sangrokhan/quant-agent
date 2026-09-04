"""Strategy: VIX-spike mean reversion into SPY, exit after N up-days.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-103):
Per QuantifiedStrategies.com's "Trading SPY And S&P 500 Using VIX" article,
the VIX behaves as a mean-reversion indicator and moves almost perfectly
inversely to SPY. The article's concrete rule: go long SPY/ES when the VIX
closes above its own upper Bollinger Band (BB, computed on VIX close, a
volatility-of-volatility spike), and exit after N consecutive up-days in
SPY (the article tested N=2 as its primary exit, "I have a fetish for this
exit"). Multiple BB-width variants (std=1.0 to std=2.5) were backtested by
the source, all producing a positive average trade return, with wider
bands (fewer, more extreme signals) giving a higher average gain per trade
but far fewer trades (std=2.5: avg 1.44%/trade, 25 trades; std=1.0: avg
0.42%/trade, 135 trades) over their 2005-2012 sample.

This is a genuinely novel data-source construction for this repo: every
prior mean-reversion strategy signaled off SPY's/the underlying asset's
OWN price action (Bollinger/RSI/CCI/z-score on the traded asset itself).
This strategy instead signals off a SEPARATE cross-asset volatility proxy
(VIX close via load_equity("^VIX", ...)) to time entries into SPY -- a
genuinely different information source, not just a different oscillator
formula on the same price series.

Signal logic
------------
- On the VIX series: rolling_mean = SMA(vix_close, bb_window),
  rolling_std = STD(vix_close, bb_window), upper_band = rolling_mean +
  bb_std * rolling_std.
- Entry (long SPY): VIX close crosses above its own upper_band (today's
  VIX close > upper_band and yesterday's VIX close <= upper_band, i.e. a
  fresh breakout, avoiding repeated daily re-entry while VIX stays high).
- Exit: after `exit_up_days` CONSECUTIVE up-days in SPY closing price
  (source's primary variant used exit_up_days=2), counted starting the day
  after entry.
- Long-only (SPY), flat otherwise. No crypto analog exists for the VIX
  itself (VIX is an S&P 500 options-implied-vol index) -- this strategy is
  equity-only by construction, similar epistemic status to the Bitcoin
  halving-cycle calendar strategy (2026-09-04-096) which was crypto-only.

Note: because this strategy's SIGNAL source (VIX) is decoupled from its
TRADED asset (SPY, or another equity ticker), generate_signals/
generate_returns accept an explicit `vix_symbol` param (default "^VIX")
and fetch the VIX series internally via data/loaders.py's load_equity
(cache-first), then align it to the price_df's index. The grid test's
loader_fn_by_asset_class only fetches the TRADED symbol's price_df and
passes it in; this module does its own secondary VIX fetch, consistent
with data/loaders.py's stated no-new-caching-logic constraint (reuses the
existing load_equity wrapper, doesn't add new fetch/cache code).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_vix_close(index: pd.DatetimeIndex, vix_symbol: str = "^VIX") -> pd.Series:
    """Fetch VIX close series via data/loaders.py's cache-first load_equity,
    aligned (forward-filled) to the traded asset's index."""
    from loaders import load_equity  # data/loaders.py, already on sys.path via strategies/ caller convention

    def _naive(ts):
        py = ts.to_pydatetime()
        return py.replace(tzinfo=None) if py.tzinfo is not None else py

    start = _naive(index.min()) if len(index) else datetime(2015, 1, 1)
    end = _naive(index.max()) if len(index) else datetime.utcnow()
    vix_df = load_equity(vix_symbol, start, end)
    vix_df = _prep(vix_df)
    vix_close = vix_df["close"].reindex(index.union(vix_df.index)).sort_index().ffill()
    vix_close = vix_close.reindex(index)
    return vix_close


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    exit_up_days: int = 2,
    vix_symbol: str = "^VIX",
) -> pd.Series:
    """Return a {0,1} long/flat position series (long the traded asset)."""
    df = _prep(price_df)
    close = df["close"]

    vix_close = _load_vix_close(df.index, vix_symbol=vix_symbol)
    vix_mean = vix_close.rolling(bb_window).mean()
    vix_stdv = vix_close.rolling(bb_window).std()
    upper_band = vix_mean + bb_std * vix_stdv

    vix_prev = vix_close.shift(1)
    upper_prev = upper_band.shift(1)
    entry_trigger = (vix_close > upper_band) & (vix_prev <= upper_prev)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    up_day_count = 0
    for i in range(n):
        if in_pos:
            if i > 0 and pd.notna(close.iloc[i]) and pd.notna(close.iloc[i - 1]) and close.iloc[i] > close.iloc[i - 1]:
                up_day_count += 1
            else:
                up_day_count = 0
            position.iloc[i] = 1
            if up_day_count >= exit_up_days:
                in_pos = False
                up_day_count = 0
        else:
            trig = entry_trigger.iloc[i]
            if bool(trig) if pd.notna(trig) else False:
                in_pos = True
                up_day_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    exit_up_days: int = 2,
    vix_symbol: str = "^VIX",
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, bb_window=bb_window, bb_std=bb_std, exit_up_days=exit_up_days, vix_symbol=vix_symbol
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
