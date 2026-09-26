"""Strategy: Symmetric long/short Bollinger Band + RSI mean reversion with an
ATR-scaled hard stop/take-profit OVERLAY on top of the band/RSI soft exits.

Hypothesis (see knowledge_base/strategies_log.jsonl for this id):
Per https://medium.com/@redsword_23261/mean-reversion-strategy-with-bollinger-bands-rsi-and-atr-based-dynamic-stop-loss-system-02adb3dca2e1
(Sword Red, Dec 2024, FMZ Quant Pine Script source, read via browser_exec
fallback after web_extract's ddgs backend could not fetch page content):
20-period Bollinger Bands (2.0 std) + 14-period RSI (30/70) identify extreme
mean-reversion setups -- long when close < lower band AND RSI < 30, short
when close > upper band AND RSI > 70. The source's own exit logic is a race
between TWO independent exits, whichever triggers first: (a) a "soft" mean-
reversion exit (close crosses back through the middle band OR RSI crosses
back through the opposite threshold), and (b) a "hard" ATR-based stop-loss
(2x ATR(14)) / take-profit (3x ATR(14)) bracket set at entry. This repo has
tested BB+RSI combos extensively (74+ prior KB hits per 2026-09-22-084) and
ATR-based stops on other signal families (e.g. 2026-09-09-004 Williams
%R+BB middle-band+ATR), but not this EXACT dual-race-exit construction
(simultaneous band/RSI reversal exit AND a fixed-multiple ATR bracket, with
whichever fires first winning) applied symmetric long+short to BB+RSI
specifically. Restricted here to LONG-only (matching this repo's existing
generate_signals {0,1} convention -- see strategies/2026-09-03_bb_meanrev_qqq_volregime.py)
since the grid/validator pipeline in this repo is built around long-only
{0,1} position series; the short side described in the source is not
implemented.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window, min_periods=window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    rsi_window: int = 14,
    rsi_oversold: float = 30.0,
    rsi_overbought: float = 70.0,
    atr_window: int = 14,
    atr_stop_mult: float = 2.0,
    atr_target_mult: float = 3.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series (long-only adaptation)."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(bb_window, min_periods=bb_window).mean()
    std = close.rolling(bb_window, min_periods=bb_window).std()
    lower_band = sma - bb_std * std

    rsi = _rsi(close, rsi_window)
    atr = _atr(df, atr_window)

    entry = (close < lower_band) & (rsi < rsi_oversold)
    soft_exit = (close > sma) | (rsi > rsi_overbought)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0

    for i in range(len(close)):
        c = close.iloc[i]
        if in_position:
            hit_stop = c <= stop_price
            hit_target = c >= target_price
            hit_soft = bool(soft_exit.iloc[i])
            if hit_stop or hit_target or hit_soft:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) and pd.notna(atr.iloc[i]) and atr.iloc[i] > 0:
                in_position = True
                entry_price = c
                stop_price = entry_price - atr_stop_mult * atr.iloc[i]
                target_price = entry_price + atr_target_mult * atr.iloc[i]
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
