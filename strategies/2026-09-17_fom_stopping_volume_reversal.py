"""Strategy: Freedom of Movement (FoM) "Stopping Volume" Reversal
("Evidence-Based Support & Resistance", Melvin Dickover, TASC April 2014).
Read this iteration via browser_exec at
https://traders.com/documentation/feedbk_docs/2014/04/traderstips.html
(EasyLanguage code disclosed directly in the article's TradeStation Traders'
Tips code section, credited to Doug McCrary/TradeStation Securities).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-118):
Dickover's FoM indicator measures how much volume was needed to move price a
given amount: rescale the day's |return| to a 1-10 scale (TheMove, relative
to its own rolling min/max over `period`) and the day's relative-volume
z-score to a 1-10 scale (TheVol), then VByM = TheVol / TheMove (high when
volume was elevated but price barely moved = "effortful, ineffective"
volume -- classic "stopping volume" evidence of support/resistance). FoM is
finally a z-score of VByM itself. The hypothesis: a FoM SPIKE (high z-score,
i.e. abnormally high volume-per-unit-of-price-move) occurring WHILE price is
in a downtrend (below its own trend SMA) signals distribution exhaustion /
support forming -- sellers unable to push price down further despite heavy
volume -- and marks a higher-quality mean-reversion long entry than a plain
volume-spike or RSI oversold signal. This is distinct from the repo's
existing volume-based entries (e.g. rvol_breakout_confirmation.py, which
uses RelativeVolume ALONE as a breakout CONFIRMATION alongside a price
breakout) because FoM specifically combines volume AND price-move magnitude
into a single ratio-of-two-rescaled-z-scores construction that has not been
tested in this repo.

Exact formula (from TASC Apr 2014 TradeStation EasyLanguage, as read this
iteration):
    AMove       = |Close[t] - Close[t-1]| / Close[t-1]
    TheMove     = 1 + (AMove - Lowest(AMove,period)) * 9 / (Highest(AMove,period) - Lowest(AMove,period))
    RelVolume   = (Volume - SMA(Volume,period)) / StdDev(Volume,period)
    TheVol      = 1 + (RelVolume - Lowest(RelVolume,period)) * 9 / (Highest(RelVolume,period) - Lowest(RelVolume,period))
    VByM        = TheVol / TheMove
    FoM         = (VByM - SMA(VByM,period)) / StdDev(VByM,period)

Signal logic:
- Downtrend filter: close < SMA(trend_window).
- Long entry: FoM crosses above fom_threshold (default 2.0 std) WHILE in a
  downtrend (stopping-volume exhaustion signal).
- Exit: close crosses back above SMA(trend_window) (trend recovery), OR a
  max_hold_days time-stop.

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


def _rescale_1_to_10(series: pd.Series, period: int) -> pd.Series:
    lo = series.rolling(period).min()
    hi = series.rolling(period).max()
    rng = hi - lo
    rescaled = 1.0 + (series - lo) * 9.0 / rng.replace(0, pd.NA)
    return rescaled.fillna(1.0)


def _fom(df: pd.DataFrame, period: int) -> pd.Series:
    close, volume = df["close"], df["volume"]

    a_move = (close - close.shift(1)).abs() / close.shift(1)
    the_move = _rescale_1_to_10(a_move, period)

    avg_vol = volume.rolling(period).mean()
    std_vol = volume.rolling(period).std()
    rel_volume = ((volume - avg_vol) / std_vol.replace(0, pd.NA)).fillna(0.0)
    the_vol = _rescale_1_to_10(rel_volume, period)

    v_by_m = (the_vol / the_move.replace(0, pd.NA)).fillna(0.0)

    avg_vbym = v_by_m.rolling(period).mean()
    std_vbym = v_by_m.rolling(period).std()
    fom = ((v_by_m - avg_vbym) / std_vbym.replace(0, pd.NA)).fillna(0.0)
    return fom


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 60,
    fom_threshold: float = 2.0,
    trend_window: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series per the FoM stopping-volume
    reversal rule."""
    df = _prep(price_df)
    close = df["close"]

    fom = _fom(df, period)
    sma_trend = close.rolling(trend_window).mean()
    downtrend = close < sma_trend

    fom_cross_up = (fom.shift(1) <= fom_threshold) & (fom > fom_threshold)
    entry = downtrend & fom_cross_up.fillna(False)
    exit_trend_recovery = close > sma_trend

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(df)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend_recovery.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
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
