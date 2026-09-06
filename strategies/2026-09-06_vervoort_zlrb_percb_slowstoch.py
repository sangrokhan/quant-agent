"""Strategy: Vervoort Zero-Lag Rainbow %B + Smoothed Stochastic confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl):
Sylvain Vervoort's "Smoothed Oscillator" (TASC Sep 2013 / LazyBear's Pine
port "Vervoort Smoothed Oscillator") builds a 10-stage "Rainbow" moving
average (10 successive SMA(2) passes of close, weighted 5:4:3:2:1:1:1:1:1:1
and divided by 20) to get a very low-lag baseline, then:
  1. Zero-lag Rainbow (ZLRB) = 2*EMA(rainbow,smooth) - EMA(EMA(rainbow,smooth),smooth)
  2. TEMA-smooth ZLRB -> tz
  3. %B of tz against its own Bollinger Bands (lengthStdev, mult) -> zlrbpercb
     ("Zero-Lag Rainbow %B", a %B oscillator, not bounded 0-100 like classic %B)
  4. rbc = average(rainbow, HLC3); fastK = clipped Stochastic of rbc over
     periodK bars; slowK = SMA(fastK, smoothK) (the "slowStoch" line)
Per the TradingView source page (LazyBear's port, crediting Vervoort's own
stated rules): "It must be bullish for a buy signal... both oscillators
must be moving up... Stoch crossing 50 is a good confirmation signal."
We operationalize this literally: long entry when zlrbpercb crosses above
its own oversold-recovery level (default 0, the oscillator's zero/mid line)
WHILE slowK is already above 50 (the stated "confirmation" gate); exit when
zlrbpercb crosses back below its overbought/exit level (default 50) OR
slowK crosses back below 50, or a max_hold_days time-stop.

First Vervoort Zero-Lag-Rainbow-%B strategy in this repo -- distinct from
all prior Stochastic-only or %B-only strategies (classic Bollinger %B mean
reversion, Fisher-Transform-of-Stochastic, Inverse-Fisher-Transform-of-
Stochastic, plain %B threshold crosses) since this combines a bespoke
10-stage zero-lag "Rainbow" smoothing with a TWO-OSCILLATOR confirmation
gate (percb AND slowK), a structurally different construction from any
single-oscillator crossover already tested.

Source: https://www.tradingview.com/script/EXtLf5PR-Indicator-Vervoort-Smoothed-Oscillator-LazyBear/
(Pine source code read directly in-browser; crediting Sylvain Vervoort,
Stocks & Commodities Sep 2013).

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


def _rainbow(close: pd.Series) -> pd.Series:
    s = [close.rolling(2).mean()]
    for _ in range(9):
        s.append(s[-1].rolling(2).mean())
    # weights 5,4,3,2,1,1,1,1,1,1 / 20 per LazyBear pine source
    weights = [5, 4, 3, 2, 1, 1, 1, 1, 1, 1]
    total = sum(w * si for w, si in zip(weights, s))
    return total / 20.0


def _tema(src: pd.Series, length: int) -> pd.Series:
    e1 = src.ewm(span=length, adjust=False).mean()
    e2 = e1.ewm(span=length, adjust=False).mean()
    e3 = e2.ewm(span=length, adjust=False).mean()
    return 3 * (e1 - e2) + e3


def _vervoort_osc(
    df: pd.DataFrame,
    length_stdev: int,
    mult: float,
    smooth: int,
    period_k: int,
    smooth_k: int,
) -> tuple[pd.Series, pd.Series]:
    close, high, low = df["close"], df["high"], df["low"]
    hlc3 = (high + low + close) / 3.0

    rainbow = _rainbow(close)
    ema1 = rainbow.ewm(span=smooth, adjust=False).mean()
    ema2 = ema1.ewm(span=smooth, adjust=False).mean()
    zlrb = 2 * ema1 - ema2
    tz = _tema(zlrb, smooth)

    hwidth = tz.rolling(length_stdev).std()

    def _wma(x):
        import numpy as np
        w = np.arange(1, len(x) + 1)
        return (x * w).sum() / w.sum()

    tz_wma = tz.rolling(length_stdev).apply(_wma, raw=True)
    zlrbpercb = (tz + mult * hwidth - tz_wma) / (2 * mult * hwidth) * 100

    rbc = (rainbow + hlc3) / 2.0
    lowest_low = low.rolling(period_k).min()
    highest_high = high.rolling(period_k).max()
    lowest_rbc = rbc.rolling(period_k).min()
    nom = rbc - lowest_low
    den = highest_high - lowest_rbc
    fast_k = (100 * nom / den.replace(0, pd.NA)).clip(0, 100)
    slow_k = fast_k.rolling(smooth_k).mean()

    return zlrbpercb, slow_k


def generate_signals(
    price_df: pd.DataFrame,
    length_stdev: int = 18,
    mult: float = 2.0,
    smooth: int = 3,
    period_k: int = 30,
    smooth_k: int = 3,
    entry_level: float = 0.0,
    exit_level: float = 50.0,
    stoch_confirm_level: float = 50.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    zlrbpercb, slow_k = _vervoort_osc(
        df, length_stdev, mult, smooth, period_k, smooth_k
    )

    long_trigger = (
        (zlrbpercb > entry_level)
        & (zlrbpercb.shift(1) <= entry_level)
        & (slow_k > stoch_confirm_level)
    )
    exit_trigger = (
        ((zlrbpercb < exit_level) & (zlrbpercb.shift(1) >= exit_level))
        | ((slow_k < stoch_confirm_level) & (slow_k.shift(1) >= stoch_confirm_level))
    )

    close = df["close"]
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(long_trigger.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1

    position.name = "position"
    return position


def generate_returns(
    price_df: pd.DataFrame,
    length_stdev: int = 18,
    mult: float = 2.0,
    smooth: int = 3,
    period_k: int = 30,
    smooth_k: int = 3,
    entry_level: float = 0.0,
    exit_level: float = 50.0,
    stoch_confirm_level: float = 50.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        length_stdev=length_stdev,
        mult=mult,
        smooth=smooth,
        period_k=period_k,
        smooth_k=smooth_k,
        entry_level=entry_level,
        exit_level=exit_level,
        stoch_confirm_level=stoch_confirm_level,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns
