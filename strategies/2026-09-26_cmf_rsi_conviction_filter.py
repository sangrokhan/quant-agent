"""Strategy: Chaikin Money Flow / RSI conviction-disagreement filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-069):
Per https://enlightenedstocktrading.com/chaikin-money-flow/'s "Filtering
Overbought and Oversold Conditions" rule family: "If the trading platform
shows oversold levels but CMF remains strong, it suggests the downward
trend may lack conviction, providing a potential buying opportunity."

This is a genuinely distinct construction from this repo's existing CMF
entries: 2026-09-07-016 (CMF zero-cross confirmed by a price breakout above
a swing high) and 2026-09-05-047 (CMF/price swing-low divergence). Here
there is no swing-point detection and no breakout confirmation -- the
signal is purely a DISAGREEMENT between two independently-computed
indicators at the SAME bar: RSI says "oversold" (price-only, no volume)
while CMF says "buying pressure present" (volume-weighted). When price and
volume disagree about conviction, the price-only oversold reading is
judged to be the less reliable one (no real seller conviction behind the
dip), so the strategy fades RSI and goes long.

Signal logic
------------
- RSI(rsi_window) computed the standard Wilder way.
- CMF(cmf_window) = sum(Money-Flow-Volume, n) / sum(Volume, n), where
  Money-Flow-Multiplier = ((Close-Low)-(High-Close))/(High-Low), naturally
  bounded [-1, 1].
- Entry (long): RSI crosses below rsi_oversold (price-only conviction says
  "sold off") AND CMF > cmf_strength_floor (volume-weighted conviction
  disagrees: sellers do NOT actually dominate flow) AND close is above
  SMA(trend_window) (only take the "lacks conviction, buy the dip" read
  inside an established uptrend, not as a standalone reversal call).
- Exit: RSI recovers back above rsi_exit (mean-reversion target reached),
  OR CMF flips negative (the disagreement resolves against us -- sellers
  really do take over), OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def _cmf(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]
    rng = (high - low).replace(0.0, 1e-12)
    mfm = ((close - low) - (high - close)) / rng
    mfv = mfm * volume
    cmf = mfv.rolling(window).sum() / volume.rolling(window).sum().replace(0.0, 1e-12)
    return cmf


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    cmf_window: int = 20,
    rsi_oversold: float = 30.0,
    rsi_exit: float = 50.0,
    cmf_strength_floor: float = 0.0,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_window)
    cmf = _cmf(df, cmf_window)
    sma_trend = close.rolling(trend_window).mean()

    rsi_prev = rsi.shift(1)
    rsi_cross_down = (rsi < rsi_oversold) & (rsi_prev >= rsi_oversold)

    entry = rsi_cross_down & (cmf > cmf_strength_floor) & (close > sma_trend)
    exit_rsi_recover = rsi >= rsi_exit
    exit_cmf_flip = cmf < 0.0

    entry = entry.fillna(False)
    exit_rsi_recover = exit_rsi_recover.fillna(False)
    exit_cmf_flip = exit_cmf_flip.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_rsi_recover.iloc[i]) or bool(exit_cmf_flip.iloc[i]) or held >= max_hold_days:
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
