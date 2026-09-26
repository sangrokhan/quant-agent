"""Strategy: Bulkowski/Adam White Trading Setup (long-only, higher-high/higher-low
entry with dual retracement + Trend Analysis Index exit).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/AdamWhiteSetup.html (Thomas
Bulkowski, read via browser_exec -- web_extract's ddgs backend cannot fetch
this domain). Originally Adam White's "A Weekly S&P Trading System" (TASC,
June 1995); Bulkowski confirmed White's own default parameters (26-week
SMA, 5% retracement, 1.2 TAI threshold) as optimal via in-sample
(2000-2005) and out-of-sample (2005-2010) tests on 567 stocks + 104 ETFs:
avg profit/trade $208-261, win rate 38-40%, W/L ratio 1.3-1.4x, median
drawdown 8-11%, avg hold 134-151 days -- but Bulkowski's own write-up
explicitly flags a "serious flaw" in the exit (median drawdown as high as
99% on some out-of-sample symbols) since the Trend Analysis Index (TAI)
can suppress the retracement exit indefinitely during a steep decline that
still LOOKS like "trending" by the TAI's range-based measure.

Source's exact MetaStock formulas (weekly bars; this repo's daily-bar
loaders approximate each N-week window as N*5 trading days, consistent
with this repo's established convention for other weekly-designed
Bulkowski setups):

    Enter long: when(llv(L,5),>,llv(L,13)) AND when(H,=,hhv(H,5))
        -- lowest low of the last 5 weeks > lowest low of the last 13
           weeks (higher-low structure), AND today's high equals the
           highest high of the last 5 weeks (higher-high breakout).

    Close Long: when(fml(#1),>,opt1) AND when(fml(#2),<,opt2)
        Formula #1 (retracement): (hhv(L,13)-L)/L > 0.05
        Formula #2 (TAI):          ((hhv(SMA(C,26),5)-llv(SMA(C,26),5))/C)*100 < 1.2
        -- exit only when price has retraced >5% off its 13-week high AND
           the TAI says price is NOT strongly trending (TAI below 1.2 =
           sideways/range regime, so the retracement signal is allowed to
           fire; a high TAI, i.e. a fast-moving 26-week SMA, suppresses
           the exit even during a steep decline -- Bulkowski's own noted
           weakness).

First strategy in this repo trading this specific higher-high/higher-low
entry construction with a TAI-gated dual-condition retracement exit (the
Vertical Horizontal Filter, Adam White's other well-known indicator, has
several prior entries in this repo -- 2026-09-04-152, 2026-09-08-057,
2026-09-14-101, 2026-09-17-028, 2026-09-20-077 -- but none test this
"Adam White Trading Setup" entry/exit RULE SET, which is a completely
different construction from VHF).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    short_window_days: int = 25,
    long_window_days: int = 65,
    retracement_pct: float = 0.05,
    tai_sma_days: int = 130,
    tai_range_days: int = 25,
    tai_threshold: float = 1.2,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Weekly windows from the source (5, 13, 26 weeks) are scaled to daily
    equivalents (x5) for this repo's daily-bar loaders:
        short_window_days=25 (5wk), long_window_days=65 (13wk),
        tai_sma_days=130 (26wk SMA period), tai_range_days=25 (the 5wk
        window over which that SMA's own high-low range is measured).
    """
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    llv_short = low.rolling(short_window_days).min()
    llv_long = low.rolling(long_window_days).min()
    hhv_short = high.rolling(short_window_days).max()

    entry = (llv_short > llv_long) & (high >= hhv_short)
    entry = entry.fillna(False)

    hhv_low_long = low.rolling(long_window_days).max()  # hhv(L,13) per source formula #1
    retracement = (hhv_low_long - low) / low

    sma_tai = close.rolling(tai_sma_days).mean()
    tai_hh = sma_tai.rolling(tai_range_days).max()
    tai_ll = sma_tai.rolling(tai_range_days).min()
    tai = ((tai_hh - tai_ll) / close) * 100.0

    exit_signal = (retracement > retracement_pct) & (tai < tai_threshold)
    exit_signal = exit_signal.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    short_window_days: int = 25,
    long_window_days: int = 65,
    retracement_pct: float = 0.05,
    tai_sma_days: int = 130,
    tai_range_days: int = 25,
    tai_threshold: float = 1.2,
) -> pd.Series:
    """Daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        short_window_days=short_window_days,
        long_window_days=long_window_days,
        retracement_pct=retracement_pct,
        tai_sma_days=tai_sma_days,
        tai_range_days=tai_range_days,
        tai_threshold=tai_threshold,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
