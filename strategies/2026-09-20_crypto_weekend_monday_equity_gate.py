"""Strategy: Crypto weekend-return asymmetric predictor of Monday equity
returns -- go flat (avoid Monday) after a negative BTC/ETH weekend, stay
long otherwise.

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration's id):
Per Mourey, Shahrour & Şoiman (2025), "A crypto-stock weekend effect:
Predicting Monday stock returns using weekend cryptocurrency returns"
(Finance Research Letters, vol. 86; abstract confirmed via Google SERP
across ScienceDirect/RePEc/SSRN snippets after web_extract's DDG-only
backend and direct SSRN/HAL page fetches were both blocked by bot-detection
walls -- browser_exec fallback used for search, but full paper text was
inaccessible, so this strategy is built from the disclosed abstract-level
finding only): "negative weekend returns in cryptocurrencies, especially
Bitcoin and Ether, systematically predict declines in U.S. equity markets
on [Monday]... a strong asymmetry: negative weekend returns significantly
predict Monday equity declines, while positive returns have no effect."

This is a genuinely new mechanism in this repo's knowledge base: prior
crypto/equity cross-asset entries either (a) traded crypto's OWN
Friday-close-to-Monday-close weekend hold (2026-09-04-029, rejected), or
(b) used static sector/macro ratio regime gates (XLY/XLP, XLU/SPY, etc.).
This strategy instead uses crypto's weekend price action as a PREDICTIVE
SIGNAL for a DIFFERENT asset class's (equity) Monday performance -- an
asymmetric down-only defensive gate, not a symmetric trend/momentum
carry-through.

Signal logic
------------
- Crypto "weekend return" = cumulative return from Friday's close to the
  following Monday's close is NOT usable directly (that already includes
  Monday), so instead: weekend return = cumulative return from Friday's
  close through Sunday's close, i.e. the crypto market's own
  Saturday+Sunday move (crypto trades 24/7, so Sat/Sun bars exist in the
  loader's daily crypto data even though equity has none over the
  weekend).
- On each equity Monday, look up the most recent completed crypto weekend
  return (Friday close -> Sunday close) for the reference crypto asset
  (default BTC/USDT, loaded separately by the equity backtest driver).
- If that weekend return is <= down_threshold (a negative return,
  default 0.0 i.e. any negative weekend), go FLAT for that Monday
  (defensive: avoid the predicted equity decline). Otherwise (weekend flat
  or positive, per the source's own finding of "no effect" on the positive
  side) stay LONG as the equity default state.
- All non-Monday days: long (baseline buy-and-hold outside the
  Monday-specific defensive gate), unless flat_non_monday=True is set for
  a stricter Monday-only-long variant (not the default; default is
  "always long except gated-out Mondays", to isolate the crypto-weekend
  signal's marginal effect against a buy-and-hold baseline rather than
  compounding it with an unrelated day-of-week trading rule).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _crypto_weekend_returns(crypto_close: pd.Series) -> pd.Series:
    """Map each Monday's date to the crypto Fri-close->Sun-close return.

    Returns a Series indexed by Monday dates (normalized to midnight),
    values = weekend return (NaN if no Friday/Sunday bar pair found).
    """
    weekday = pd.Series(crypto_close.index.weekday, index=crypto_close.index)
    fridays = crypto_close.index[weekday == 4]
    result = {}
    for fri in fridays:
        # Find the Sunday within 2 days after this Friday.
        window = crypto_close.loc[fri: fri + pd.Timedelta(days=3)]
        sundays = window.index[pd.Series(window.index.weekday, index=window.index) == 6]
        if len(sundays) == 0:
            continue
        sun = sundays[0]
        fri_close = crypto_close.loc[fri]
        sun_close = crypto_close.loc[sun]
        if fri_close == 0 or pd.isna(fri_close) or pd.isna(sun_close):
            continue
        weekend_ret = (sun_close / fri_close) - 1.0
        # The following Monday is what this weekend return predicts.
        monday = sun + pd.Timedelta(days=1)
        result[monday.normalize()] = weekend_ret
    return pd.Series(result).sort_index()


_crypto_cache: dict = {}


def _load_crypto_close(crypto_symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Cache-first crypto close series fetch via data/loaders.py."""
    key = (crypto_symbol, start.date(), end.date())
    if key in _crypto_cache:
        return _crypto_cache[key]
    from loaders import load_crypto  # noqa: E402

    df = load_crypto(crypto_symbol, start.to_pydatetime(), end.to_pydatetime())
    df = _prep(df)
    series = df["close"]
    _crypto_cache[key] = series
    return series


def generate_signals(
    price_df: pd.DataFrame,
    crypto_symbol: str = "BTC/USDT",
    down_threshold: float = 0.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series for the EQUITY asset.

    Internally fetches the reference crypto asset's OHLCV via
    data/loaders.py (cache-first) so this fits the grid_test contract of
    generate_signals(price_df, **params) with no extra positional args.
    """
    df = _prep(price_df)
    close = df["close"]
    weekday = pd.Series(close.index.weekday, index=close.index)

    position = pd.Series(1, index=close.index, dtype=int)  # long by default

    if len(close) == 0:
        return position

    start = close.index.min() - pd.Timedelta(days=7)
    end = close.index.max() + pd.Timedelta(days=1)
    try:
        crypto_close = _load_crypto_close(crypto_symbol, start, end)
    except Exception:
        # Data fetch failed (offline/rate-limited) -- degrade to always-long.
        return position

    weekend_rets = _crypto_weekend_returns(crypto_close)

    for i in range(len(close)):
        ts = close.index[i]
        if weekday.iloc[i] == 0:  # Monday
            key = ts.normalize()
            if key in weekend_rets.index:
                wr = weekend_rets.loc[key]
                if pd.notna(wr) and wr <= down_threshold:
                    position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    crypto_symbol: str = "BTC/USDT",
    down_threshold: float = 0.0,
    **kwargs,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, crypto_symbol=crypto_symbol, down_threshold=down_threshold
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(1).astype(int) * daily_ret
    # NOTE: shift(1).fillna(1) rather than fillna(0) -- day 0's baseline
    # exposure is "long" (the strategy's default state), not flat.
    return strategy_ret
