"""Strategy: DMI Stochastic Reversal (Barbara Star, PhD, TASC Jan 2013 "The
DMI Stochastic"), read this iteration via browser_exec at
http://traders.com/documentation/feedbk_docs/2013/01/traderstips.html
(EasyLanguage/MetaStock formulas disclosed directly in the article's
TradeStation and MetaStock Traders' Tips code sections).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-113):
The DMI Oscillator (DMIOsc = +DI(n) - -DI(n), Wilder's directional indicators)
gives the trend DIRECTION; a stochastic-style normalization of DMIOsc over a
short lookback (percent-rank of DMIOsc within its own recent high/low range,
summed over a short window per the article's exact formula) gives an
OVERBOUGHT/OVERSOLD READING OF THE OSCILLATOR ITSELF (not of price), which the
article says marks better-quality reversal entries than a raw DI crossover.
This is distinct from the repo's 20+ prior ADX/DMI crossover/threshold
entries (e.g. 2026-09-03-017 rejected, 2026-09-11-097 rejected) because none
of them apply a stochastic normalization to the oscillator series itself --
this iteration tests that specific, previously-untested construction.

Exact formula (from TASC Jan 2013 TradeStation EasyLanguage / MetaStock code,
as read this iteration):
    DMIOsc   = +DI(dmi_length) - -DI(dmi_length)
    HighestOsc = Highest(DMIOsc, hl_period)
    LowestOsc  = Lowest(DMIOsc, hl_period)
    DMIStoch = 100 * Sum(DMIOsc - LowestOsc, sum_period) /
                     Sum(HighestOsc - LowestOsc, sum_period)
    DMIStochMA = SMA(DMIStoch, ma_period)

Signal logic (combining the article's disclosed entry filter -- "long
entries exist when the DMI oscillator is above zero" -- with its disclosed
"DMI Stochastic Reversal" ShowMe crossover-of-its-own-MA signal):
- Long entry: DMIOsc > 0 (bullish directional trend) AND DMIStoch crosses
  above DMIStochMA (bullish reversal confirmation within that trend).
- Exit: DMIOsc turns <= 0 (trend flips bearish) OR DMIStoch crosses below
  DMIStochMA (reversal signal fades).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Given an OHLCV DataFrame (columns: timestamp, open, high, low,
        close, volume; as returned by data/loaders.py), returns the
        strategy's daily return series (position-weighted, no transaction
        costs applied here -- that's handled separately by
        check_transaction_cost_survival).

    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index
        (1 = long, 0 = flat).
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wilder_dmi(df: pd.DataFrame, length: int) -> pd.Series:
    """Return DMI Oscillator = +DI(length) - -DI(length), Wilder smoothing."""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_dm = pd.Series(plus_dm, index=df.index)
    minus_dm = pd.Series(minus_dm, index=df.index)

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    # Wilder smoothing (equivalent to EMA with alpha=1/length via RMA)
    atr = tr.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    plus_dm_sm = plus_dm.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    minus_dm_sm = minus_dm.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()

    plus_di = 100.0 * (plus_dm_sm / atr.replace(0, np.nan))
    minus_di = 100.0 * (minus_dm_sm / atr.replace(0, np.nan))

    dmi_osc = (plus_di - minus_di).fillna(0.0)
    return dmi_osc


def _dmi_stochastic(dmi_osc: pd.Series, hl_period: int, sum_period: int) -> pd.Series:
    highest_osc = dmi_osc.rolling(hl_period).max()
    lowest_osc = dmi_osc.rolling(hl_period).min()

    numerator = (dmi_osc - lowest_osc).rolling(sum_period).sum()
    denominator = (highest_osc - lowest_osc).rolling(sum_period).sum()

    dmi_stoch = 100.0 * numerator / denominator.replace(0, np.nan)
    return dmi_stoch.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    dmi_length: int = 10,
    hl_period: int = 3,
    sum_period: int = 3,
    ma_period: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series per the DMI Stochastic
    Reversal rule (TASC Jan 2013, Barbara Star)."""
    df = _prep(price_df)

    dmi_osc = _wilder_dmi(df, dmi_length)
    dmi_stoch = _dmi_stochastic(dmi_osc, hl_period, sum_period)
    dmi_stoch_ma = dmi_stoch.rolling(ma_period).mean()

    trend_up = dmi_osc > 0
    cross_over = (dmi_stoch.shift(1) <= dmi_stoch_ma.shift(1)) & (dmi_stoch > dmi_stoch_ma)
    cross_under = (dmi_stoch.shift(1) >= dmi_stoch_ma.shift(1)) & (dmi_stoch < dmi_stoch_ma)

    entry = trend_up & cross_over.fillna(False)
    exit_trend_flip = ~trend_up
    exit_cross_under = cross_under.fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        if in_position:
            if bool(exit_trend_flip.iloc[i]) or bool(exit_cross_under.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
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
