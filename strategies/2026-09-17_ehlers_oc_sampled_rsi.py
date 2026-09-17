"""Strategy: Ehlers OC-Sampled RSI (Open+Close average price input).

Source: TASC (Technical Analysis of Stocks & Commodities) March 2023,
John F. Ehlers, "Every Little Bit Helps", via
https://traders.com/Documentation/FEEDbk_docs/2023/03/TradersTips.html
(visited this iteration, see knowledge_base/visited_pages.jsonl).

Ehlers' core proposal: noise in a price-derived indicator (his own example
is RSI) can be reduced simply by averaging the OPEN and CLOSE of each bar
as the sampled "price" fed into the indicator, instead of using only the
closing price:

    CTest  = RSI(Close, 14)               # traditional, noisier
    OCTest = RSI((Open + Close) / 2, 14)   # OC-sampled, source's proposal

This is a general DATA-SAMPLING technique (not an indicator formula per
se) applicable to any close-based oscillator -- first "OC-sampled" input
strategy in this repo (0 prior KB hits for this technique), distinct from
every existing RSI-family entry (classic RSI, StochRSI, Cutler RSI, Connors
RSI, Dynamic Zone RSI, Vervoort Rainbow-smoothed RSI, Apirine Slow RSI) all
of which apply their smoothing/normalization AFTER computing on raw close,
never changing the underlying sampled price series itself.

Trading rule (standard oversold-recovery RSI crossover, this repo's usual
treatment for a bare oscillator with no disclosed specific strategy rule
in the source): long entry when OC-sampled RSI crosses up through
`oversold` from below; exit when it crosses back down through `overbought`
or a `max_hold_days` time-stop, gated by a `close > SMA(trend_window)`
regime filter (this repo's standard robustness addition for oscillator
crossovers).

Interface contract (see validation/grid_test.py, validation/validators.py):
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


def _wilder_rsi(price: pd.Series, period: int) -> pd.Series:
    delta = price.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 10,
    oversold: float = 40.0,
    overbought: float = 70.0,
    trend_window: int = 150,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    oc_sample = (open_ + close) / 2.0

    rsi = _wilder_rsi(oc_sample, rsi_period)
    trend_sma = close.rolling(trend_window).mean()

    cross_up = (rsi > oversold) & (rsi.shift(1) <= oversold)
    cross_down = (rsi < overbought) & (rsi.shift(1) >= overbought)
    trend_ok = close > trend_sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]) and bool(trend_ok.iloc[i]):
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
