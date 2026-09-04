"""Strategy: Elder Ray Index (Bull Power / Bear Power) long-only trend strategy.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-110):
Elder Ray Index (Alexander Elder, 1989; via
https://www.quantifiedstrategies.com/elder-ray-indicator/) uses a 13-day EMA
to define trend, plus two oscillators: Bull Power = High - EMA, Bear Power =
Low - EMA. The classic long entry rule is: trend is up (EMA rising) AND Bear
Power is negative but rising (bears are losing conviction even though price
still dips below the EMA on the lows) -- i.e. buy while bears are still
"in the air" but weakening, rather than waiting for full confirmation.
Exit is the mirror short-entry condition (EMA falling AND Bull Power positive
but falling), which we treat here as a flat/exit signal rather than an actual
short, since the source's own AmiBroker backtest found shorting performed
poorly across assets while the long side had a modest edge (SPY 2000-2020:
CAGR 3.6% vs 6.25% buy-hold, profit factor 1.5, 59% time invested). This is a
genuinely new indicator family for this repo (Bull/Bear Power has 0 prior
entries in strategies_index.jsonl) and is distinct from every prior
SMA/EMA-crossover or Bollinger/RSI mean-reversion strategy already tested:
it conditions entry on the *momentum of the distance* between price extremes
(high/low) and the trend EMA, not on price crossing a band or a moving
average directly.

Signal logic
------------
- ema = EMA(close, ema_window) (default 13, per source's classic setting;
  source's own sweep found longer EMAs, e.g. 16, sometimes outperformed).
- bull_power = high - ema
- bear_power = low - ema
- Long entry: ema is rising (ema > ema.shift(1)) AND bear_power < 0 AND
  bear_power > bear_power.shift(1) (still negative but improving).
- Exit (go flat): ema is falling (ema < ema.shift(1)) AND bull_power > 0 AND
  bull_power < bull_power.shift(1) (mirror short-entry condition, used here
  as an exit rather than an actual short entry -- no order-placement, no
  short exposure, per SAFETY.md and the source's own finding that shorting
  underperforms).
- Otherwise: hold current position (no signal to flip).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
    ema_window: int = 13,
) -> pd.Series:
    """Return a {0,1} long/flat position series per the Elder Ray rule."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    ema = close.ewm(span=ema_window, adjust=False).mean()
    bull_power = high - ema
    bear_power = low - ema

    ema_rising = ema > ema.shift(1)
    ema_falling = ema < ema.shift(1)

    long_entry = ema_rising & (bear_power < 0) & (bear_power > bear_power.shift(1))
    exit_signal = ema_falling & (bull_power > 0) & (bull_power < bull_power.shift(1))

    long_entry = long_entry.fillna(False)
    exit_signal = exit_signal.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(long_entry.iloc[i]):
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
