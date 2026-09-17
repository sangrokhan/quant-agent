"""Strategy: RSI(2) Setup + 2-Bar Down-Close Reversal Pattern with EMA200
Trend Filter, Stop-Entry, and Dual Exit ("A Trading Method For The Long
Haul", Donald W. Pendergast Jr., 2014 Bonus Issue of Stocks & Commodities,
TASC May 2014 Traders' Tips). Read this iteration via browser_exec at
https://traders.com/documentation/feedbk_docs/2014/05/traderstips.html
(EasyLanguage code disclosed directly in the article's TradeStation Traders'
Tips code section, credited to Doug McCrary/TradeStation Securities).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-119):
Pendergast's system is a STATE MACHINE, distinct from the repo's existing
RSI(2) family (rsi2_meanrev_trend200.py's simple threshold-cross,
rsi2_holygrail_nextopen_timing.py's next-open entry, etc.) in three specific
ways: (1) RSI(2) dropping below an extreme oversold level (5) ARMS a
"setup" flag that persists until either a position is entered or RSI(2)
rises above an overbought level (95) -- not a same-bar threshold check;
(2) the actual entry additionally requires a concrete 2-BAR DOWN-CLOSE
REVERSAL PATTERN (today's high < yesterday's high AND both today's and
yesterday's candles closed below their own opens) confirming the oversold
condition with price action, not RSI alone; (3) entry is a STOP order above
today's high (not an immediate market/next-open buy), so the trade only
triggers if price actually starts reversing upward. Exit uses TWO
independent rules: a 3-bar trailing stop (lowest low of the last 3 bars) OR
a fast EMA(6) close-crossunder, whichever hits first -- a tighter exit
discipline than most of the repo's RSI2 variants.

Exact formula/logic (from TASC May 2014 TradeStation EasyLanguage, as read
this iteration; long-only, source is long-only too):
    RSISetUpOK: armed True when (not in position AND RSI(2) < oversold_level);
                disarmed False when (in position OR RSI(2) > overbought_level);
                else carries forward its previous value (persistent state).
    ReversalOK: High[t] < High[t-1] AND Close[t] < Open[t] AND Close[t-1] < Open[t-1]
    EMAFilterOK: Close > EMA(ema_filter_length)
    Entry (next bar, stop order approximated here as same-bar trigger since
        this repo works with daily OHLC bars, not intrabar order routing):
        RSISetUpOK AND ReversalOK AND EMAFilterOK, triggered when High[t]
        exceeds High[t-1] + a small tick (approximated: enter on the FIRST
        bar after the setup where high exceeds the setup bar's high).
    Exit: Low crosses under Lowest(Low[1], num_bars_for_trail) [3-bar trail]
          OR Close crosses under EMA(ema_length) [fast EMA, 6-period].

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
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


def _rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    num_bars_for_trail: int = 3,
    ema_length: int = 6,
    ema_filter_length: int = 200,
    rsi_length: int = 2,
    rsi_oversold: float = 5.0,
    rsi_overbought: float = 95.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series per Pendergast's
    RSI-setup + reversal-pattern + EMA200-filter system."""
    df = _prep(price_df)
    open_, high, low, close = df["open"], df["high"], df["low"], df["close"]

    rsi_val = _rsi(close, rsi_length)
    ema_fast = close.ewm(span=ema_length, adjust=False).mean()
    ema_filter = close.ewm(span=ema_filter_length, adjust=False).mean()

    ema_filter_ok = close > ema_filter
    reversal_ok = (high < high.shift(1)) & (close < open_) & (close.shift(1) < open_.shift(1))

    trail_stop = low.shift(1).rolling(num_bars_for_trail).min()

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    rsi_setup_ok = False
    pending_entry_high = None  # stop-entry trigger level, set the bar after setup+reversal fire
    for i in range(len(df)):
        # Update RSISetUpOK state (persistent, evaluated before this bar's action)
        if not in_position and rsi_val.iloc[i] < rsi_oversold:
            rsi_setup_ok = True
        elif in_position or rsi_val.iloc[i] > rsi_overbought:
            rsi_setup_ok = False

        if in_position:
            exit_trail = not pd.isna(trail_stop.iloc[i]) and low.iloc[i] < trail_stop.iloc[i]
            exit_ema = close.iloc[i] < ema_fast.iloc[i]
            if exit_trail or exit_ema:
                in_position = False
                pending_entry_high = None
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            # Check whether a pending stop-entry (armed on a prior bar) triggers today
            entered_today = False
            if pending_entry_high is not None and high.iloc[i] > pending_entry_high:
                in_position = True
                entered_today = True
                pending_entry_high = None
                position.iloc[i] = 1

            if not entered_today:
                # Arm a new pending stop-entry if setup+reversal+filter all align this bar
                if rsi_setup_ok and bool(reversal_ok.iloc[i]) and bool(ema_filter_ok.iloc[i]):
                    pending_entry_high = float(high.iloc[i])
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
