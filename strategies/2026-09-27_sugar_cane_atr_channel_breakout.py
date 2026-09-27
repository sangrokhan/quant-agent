"""Strategy: Sugar futures (CANE ETF proxy) 350-day SMA + 7-day ATR channel
breakout (Turtle-style channel, per QuantifiedStrategies.com's own disclosed
backtest).

Hypothesis (2026-09-27 KB entry, this iteration): per
https://www.quantifiedstrategies.com/sugar-trading-strategy/ (Oddmund
Groette), the only Turtle-style trend-following variant the source found to
show any promise on sugar futures was: buy when price breaks above the
350-day moving average PLUS a 7-day ATR band, sell (exit) when price breaks
below the 350-day moving average MINUS a 7-day ATR band. Source's own
framing: sugar is a notoriously hard-to-trade commodity with a low win
ratio but a few large winning trend moves that recoup many small losers
(classic trend-following payoff profile) -- source itself states "We are
not trading any sugar strategy" (their own caveat about difficulty), but
the backtest itself is disclosed as the best-performing variant they found.
Adapted here to CANE (Teucrium Sugar Fund ETF, a continuously-rolled sugar
futures proxy tradable via yfinance, since data/loaders.py has no raw
futures-contract data source) -- first Sugar/CANE strategy and first
soft-commodity (ex-UNG/USO/UGA already tested) strategy in this repo (0
prior KB hits for "sugar"/"CANE"/"coffee futures").

Signal logic (exact source rule, long-only per SAFETY.md so the "sell"
leg is treated purely as an exit, not a short entry):
    upper_band = SMA(close, sma_window) + atr_mult * ATR(atr_window)
    lower_band = SMA(close, sma_window) - atr_mult * ATR(atr_window)
    entry: close crosses above upper_band
    exit:  close crosses below lower_band, or a max_hold_days time-stop
           (added per this repo's standard convention -- the source's own
           system is a pure reversal system with no time-stop, but an
           explicit hold cap avoids indefinite single-trade concentration
           risk in this repo's validator framework)

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 350,
    atr_window: int = 7,
    atr_mult: float = 1.0,
    max_hold_days: int = 120,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(sma_window).mean()
    atr = _atr(df, atr_window)
    upper_band = sma + atr_mult * atr
    lower_band = sma - atr_mult * atr

    cross_up = (close > upper_band) & (close.shift(1) <= upper_band.shift(1))
    cross_down = (close < lower_band) & (close.shift(1) >= lower_band.shift(1))
    entry = cross_up.fillna(False)
    exit_signal = cross_down.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
