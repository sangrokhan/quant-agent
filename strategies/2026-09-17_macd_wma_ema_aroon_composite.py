"""Strategy: MACD-sign + WMA/EMA trend-position + Aroon crossover composite
(Barbara Star, TASC May 2016 "Zero In On The MACD").

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-134):
Per Barbara Star's "Zero In On The MACD" (TASC May 2016; TradeStation
EasyLanguage "PaintBar: Warning Symbols" code disclosed at
https://traders.com/Documentation/FEEDbk_docs/2016/05/TradersTips.html),
a bullish continuation setup is confirmed when THREE independent signals
align: (1) classic MACD(12,26) is positive (uptrend momentum), (2) close is
above its 34-period WMA while the 55-period EMA is also above that same WMA
(source's own "EMAValue > WMAValue and Close > WMAValue" condition, drawn
as a bullish warning label), and (3) the Aroon Up(25) line has just crossed
over the Aroon Down(25) line (source's own "AroonUpValue crosses over
AroonDnValue" condition, drawn as an "A" label). The source presents these
as three independent visual warning overlays on a discretionary trader's
chart, not a combined mechanical rule -- this iteration's own contribution
is combining all three into one long-entry trigger and adding a mechanical
exit (MACD turning negative, or a max_hold_days time-stop).

Signal logic
------------
- macd = EMA(close, fast) - EMA(close, slow); macd_positive = macd > 0.
- wma = WMA(close, wma_length); ema = EMA(close, ema_length).
- trend_ok = (close > wma) AND (ema > wma)  [source's "EMA above WMA and
  price above WMA" bullish warning condition].
- aroon_up/aroon_down over aroon_length (Chande's original 100*(N-periods
  since N-period high)/N formulation).
- aroon_cross = aroon_up crosses over aroon_down.
- Entry (long): aroon_cross AND macd_positive AND trend_ok (all three
  conditions active on the same bar).
- Exit: macd turns non-positive, OR after max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _aroon(df: pd.DataFrame, length: int):
    high = df["high"]
    low = df["low"]

    def _periods_since_max(window: pd.Series) -> float:
        return float(len(window) - 1 - window.values.argmax())

    def _periods_since_min(window: pd.Series) -> float:
        return float(len(window) - 1 - window.values.argmin())

    periods_since_high = high.rolling(length + 1).apply(_periods_since_max, raw=False)
    periods_since_low = low.rolling(length + 1).apply(_periods_since_min, raw=False)

    aroon_up = 100.0 * (length - periods_since_high) / length
    aroon_down = 100.0 * (length - periods_since_low) / length
    return aroon_up, aroon_down


def generate_signals(
    price_df: pd.DataFrame,
    macd_fast: int = 12,
    macd_slow: int = 26,
    wma_length: int = 34,
    ema_length: int = 55,
    aroon_length: int = 25,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    macd = close.ewm(span=macd_fast, adjust=False).mean() - close.ewm(span=macd_slow, adjust=False).mean()
    macd_positive = macd > 0

    weights = pd.Series(range(1, wma_length + 1), dtype=float)
    wma = close.rolling(wma_length).apply(lambda w: (w * weights.values).sum() / weights.sum(), raw=True)
    ema = close.ewm(span=ema_length, adjust=False).mean()

    trend_ok = (close > wma) & (ema > wma)

    aroon_up, aroon_down = _aroon(df, aroon_length)
    aroon_cross = (aroon_up > aroon_down) & (aroon_up.shift(1) <= aroon_down.shift(1))

    entry = aroon_cross.fillna(False) & macd_positive.fillna(False) & trend_ok.fillna(False)
    exit_macd_flip = ~macd_positive.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_macd_flip.iloc[i]) or held >= max_hold_days:
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
