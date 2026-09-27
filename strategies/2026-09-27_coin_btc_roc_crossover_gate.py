"""Strategy: COIN/BTC ratio Rate-of-Change (momentum) crossover confirmation
gate on a primary asset's SMA trend-following signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Coinbase (COIN) is a crypto-exchange operator whose direct listing (April
14, 2021) coincided almost exactly with a Bitcoin cycle top, a pattern
widely discussed in retrospectives (per cryptoslate.com's "New Bitcoin
'top signal' is in" and stockanalysis.com's IPO-to-impact overview, read
via web_search this iteration) as reflecting a structural link between
crypto-native equity sentiment and the underlying asset's own cycle. COIN's
revenue is overwhelmingly trading-fee-driven, so its stock price should
lead/confirm shifts in crypto trading ACTIVITY and volume, distinct from
MSTR (a passive balance-sheet BTC holder, already tested as a mNAV-level
regime gate, 2026-09-20-040/041) and MARA (a bitcoin MINER with operating
leverage on mining margins, already tested as a z-score overshoot-
confirmation gate, 2026-09-20-043/044) -- COIN's economic exposure is to
crypto TRADING VOLUME/ACTIVITY, not treasury holdings or mining costs.

This strategy tests the RATE-OF-CHANGE (momentum) of the COIN/BTC ratio,
distinct from both prior proxy constructions (MSTR = ratio LEVEL vs its own
SMA; MARA = ratio Z-SCORE overshoot): compute a rolling ROC of the
COIN/BTC price ratio over roc_window bars, and take its own EMA(signal_window)
as a signal line. A bullish crossover (ROC crosses above its signal line)
confirms accelerating crypto-native equity enthusiasm relative to BTC's own
move -- gate a plain SMA(trend_window) trend-following signal on the
primary asset to trade ONLY while this ROC-crossover confirmation is
currently bullish.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def _coin_btc_roc_crossover(index: pd.DatetimeIndex, roc_window: int, signal_window: int) -> pd.Series:
    from loaders import load_equity, load_crypto

    start = index.min() - pd.Timedelta(days=(roc_window + signal_window) * 3 + 30)
    end = index.max() + pd.Timedelta(days=5)

    coin = load_equity("COIN", start.to_pydatetime(), end.to_pydatetime(), interval="1d")
    btc = load_crypto("BTC/USDT", start.to_pydatetime(), end.to_pydatetime(), interval="1d")

    coin = _prep(coin)["close"].rename("coin")
    btc = _prep(btc)["close"].rename("btc")

    merged = pd.concat([coin, btc], axis=1).dropna()
    ratio = merged["coin"] / merged["btc"]

    roc = ratio.pct_change(roc_window)
    signal_line = roc.ewm(span=signal_window, adjust=False).mean()

    bullish = roc > signal_line
    bullish = bullish.reindex(index, method="ffill")
    return bullish


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    roc_window: int = 20,
    signal_window: int = 10,
    min_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    min_hold_days: once a position changes (enter or exit), hold it for at
        least this many bars before allowing another flip -- reduces
        whipsaw trade frequency and transaction-cost drag.
    """
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    base_trend = close > sma

    confirmation = _coin_btc_roc_crossover(close.index, roc_window, signal_window)

    raw_position = (base_trend & confirmation.fillna(False)).astype(int)

    n = len(raw_position)
    raw_v = raw_position.values
    state = raw_v.copy()
    last_change = 0
    for i in range(1, n):
        if state[i] != state[i - 1]:
            if (i - last_change) < min_hold_days:
                state[i] = state[i - 1]
            else:
                last_change = i

    position = pd.Series(state, index=close.index).astype(bool)
    signal = position.shift(1).fillna(False).astype(int)
    return signal


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    roc_window: int = 20,
    signal_window: int = 10,
    min_hold_days: int = 5,
) -> pd.Series:
    """Daily strategy returns, position-weighted, no transaction costs."""
    df = _prep(price_df)
    close = df["close"]
    positions = generate_signals(
        price_df,
        trend_window=trend_window,
        roc_window=roc_window,
        signal_window=signal_window,
        min_hold_days=min_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = positions * daily_ret
    return strat_ret.fillna(0.0)
