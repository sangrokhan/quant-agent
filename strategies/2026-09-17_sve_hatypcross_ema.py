"""Strategy: EMA Typical Price / Heikin-Ashi Close Crossover with candle-body
confirmation ("An Expert Of A System", Sylvain Vervoort, TASC October 2013),
read this iteration via browser_exec at
https://traders.com/documentation/feedbk_docs/2013/10/traderstips.html
(EasyLanguage code disclosed directly in the article's TradeStation Traders'
Tips code section).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-114):
Comparing an EMA of the TYPICAL PRICE (H+L+C)/3-style, here (O+H+L+C)/4) to an
EMA of a HEIKIN-ASHI SMOOTHED CLOSE (_SVE_haClose, itself a further-smoothed
variant of the standard Heikin-Ashi close recursion, see formula below) gives
a de-noised trend-direction cross that's confirmed only when the raw candle
body agrees (close vs open), avoiding whipsaw flips inside choppy/doji bars.
This is distinct from the repo's prior Heikin-Ashi entries (e.g.
2026-09-11-086's haClose/haOpen candle-color-flip, and 2026-09-04's
heikin_ashi_momentum) because none compare EMA(typical price) to EMA of
Vervoort's specific SVE_haClose recursion with a same-bar candle-direction
gate on the cross itself.

Exact formula (from TASC Oct 2013 TradeStation EasyLanguage, as read this
iteration):
    _SVE_haOpen[0]  = Open                                    (bar 0)
    _SVE_haOpen[t]  = ( (O[t-1]+H[t-1]+L[t-1]+C[t-1])/4 + _SVE_haOpen[t-1] ) / 2
    _SVE_haClose[t] = ( (O[t]+H[t]+L[t]+C[t])/4
                         + _SVE_haOpen[t]
                         + max(H[t], _SVE_haOpen[t])
                         + min(L[t], _SVE_haOpen[t]) ) / 4
    AVGTyp = EMA(TypicalPrice=(H+L+C)/3, ema_typ_len)   # article's own function is (O+H+L+C)/4-based via TypicalPrice built-in; TradeStation's built-in TypicalPrice = (H+L+C)/3, used verbatim here
    AVGhaC = EMA(_SVE_haClose, ema_hac_len)
    MAcross = 1 if (AVGTyp > AVGhaC AND Close > Open)   [carries forward otherwise]
            = 0 if (AVGTyp < AVGhaC AND Close < Open)

Signal logic: long while MAcross == 1 (state variable that only flips on
those exact confirmed-cross conditions, else holds its last value -- exactly
per the disclosed EasyLanguage `if/else if` with no `else` branch, i.e. a
persistent state machine, not a per-bar recomputed flag).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _sve_ha_close(df: pd.DataFrame) -> pd.Series:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    n = len(df)
    ha_open = pd.Series(index=df.index, dtype=float)
    ha_close = pd.Series(index=df.index, dtype=float)

    prev_ha_open = None
    for i in range(n):
        if i == 0:
            cur_ha_open = float(o.iloc[i])
        else:
            prev_bar_avg = (o.iloc[i - 1] + h.iloc[i - 1] + l.iloc[i - 1] + c.iloc[i - 1]) / 4.0
            cur_ha_open = (prev_bar_avg + prev_ha_open) / 2.0
        ha_open.iloc[i] = cur_ha_open

        bar_avg = (o.iloc[i] + h.iloc[i] + l.iloc[i] + c.iloc[i]) / 4.0
        cur_ha_close = (
            bar_avg + cur_ha_open + max(h.iloc[i], cur_ha_open) + min(l.iloc[i], cur_ha_open)
        ) / 4.0
        ha_close.iloc[i] = cur_ha_close
        prev_ha_open = cur_ha_open

    return ha_close


def generate_signals(
    price_df: pd.DataFrame,
    ema_typ_len: int = 5,
    ema_hac_len: int = 8,
) -> pd.Series:
    """Return a {0,1} long/flat position series per the SVEHaTypCross rule."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]

    typical_price = (h + l + c) / 3.0
    sve_ha_close = _sve_ha_close(df)

    avg_typ = typical_price.ewm(span=ema_typ_len, adjust=False).mean()
    avg_hac = sve_ha_close.ewm(span=ema_hac_len, adjust=False).mean()

    bullish_cross = (avg_typ > avg_hac) & (c > o)
    bearish_cross = (avg_typ < avg_hac) & (c < o)

    # MAcross is a persistent state machine: only updates on an exact
    # confirmed condition, otherwise carries forward its previous value
    # (per the disclosed EasyLanguage if/elseif with no else branch).
    position = pd.Series(0, index=df.index, dtype=int)
    state = 0
    for i in range(len(df)):
        if bool(bullish_cross.iloc[i]):
            state = 1
        elif bool(bearish_cross.iloc[i]):
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
