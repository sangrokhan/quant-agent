"""Strategy: Parabolic SAR (Wilder) flip signal, SMA-trend-filtered.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-042):
Per QuantifiedStrategies.com's Parabolic SAR article, the classic Wilder
Parabolic SAR (acceleration factor starting at 0.02, incrementing by 0.02
per new swing extreme up to a max of 0.20) flipping from above price to
below price signals the start of an uptrend. The source's own SPY backtest
found NO reliably profitable STANDALONE SAR strategy -- it explicitly
recommends pairing SAR with a trend filter (moving average, RSI, ADX) to
improve reliability, since SAR whipsaws badly in sideways/choppy markets.
This strategy implements exactly that: long-only entry when SAR flips
bullish (below price) AND close > SMA(trend_window) (regime confirmation),
exit on SAR flipping bearish (above price) or trend filter breaking.

Parabolic SAR formula (standard Wilder):
    SAR_next = SAR_prev + AF * (EP - SAR_prev)
    EP = extreme point (highest high in uptrend, lowest low in downtrend)
    AF starts at af_start, increments by af_step on each new EP, capped
    at af_max. On a flip (price crosses the SAR), SAR resets to the prior
    EP, AF resets to af_start, and EP resets to the current bar's
    high/low.

This is an inherently sequential (path-dependent) indicator -- computed
with an explicit Python loop rather than vectorized pandas ops, matching
the reference-shape convention already used for other stateful in-position
loops in this repo (see strategies/2026-09-04_vortex_crossover_trend.py's
position-tracking loop).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _parabolic_sar(
    df: pd.DataFrame,
    af_start: float = 0.02,
    af_step: float = 0.02,
    af_max: float = 0.20,
) -> pd.Series:
    """Return the Parabolic SAR line as a pd.Series aligned to df.index."""
    high = df["high"].values
    low = df["low"].values
    n = len(df)
    sar = [None] * n
    if n == 0:
        return pd.Series(sar, index=df.index, dtype=float)

    # Initialize: assume uptrend start, SAR = first bar's low, EP = first high.
    trend_up = True
    sar_val = low[0]
    ep = high[0]
    af = af_start
    sar[0] = sar_val

    for i in range(1, n):
        prev_sar = sar_val
        sar_val = prev_sar + af * (ep - prev_sar)

        if trend_up:
            # SAR must not be above the prior two bars' lows.
            sar_val = min(sar_val, low[i - 1], low[i - 2] if i >= 2 else low[i - 1])
            if low[i] < sar_val:
                # Flip to downtrend.
                trend_up = False
                sar_val = ep  # reset SAR to the prior extreme point
                ep = low[i]
                af = af_start
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
        else:
            sar_val = max(sar_val, high[i - 1], high[i - 2] if i >= 2 else high[i - 1])
            if high[i] > sar_val:
                # Flip to uptrend.
                trend_up = True
                sar_val = ep
                ep = high[i]
                af = af_start
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)

        sar[i] = sar_val

    return pd.Series(sar, index=df.index, dtype=float)


def generate_signals(
    price_df: pd.DataFrame,
    af_start: float = 0.02,
    af_step: float = 0.02,
    af_max: float = 0.20,
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long-only entry: SAR flips bullish (close crosses above SAR, i.e. SAR
    goes from above price to below) AND close > SMA(trend_window). Exit on
    SAR flipping bearish (close crosses back below SAR) or the trend filter
    breaking.
    """
    df = _prep(price_df)
    close = df["close"]

    sar = _parabolic_sar(df, af_start=af_start, af_step=af_step, af_max=af_max)
    sma_trend = close.rolling(trend_window).mean()

    price_above_sar = close > sar
    bullish_flip = price_above_sar & (~price_above_sar.shift(1).fillna(False))
    bearish_flip = (~price_above_sar) & (price_above_sar.shift(1).fillna(False))

    trend_ok = (close > sma_trend).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(bearish_flip.iloc[i]) or not bool(trend_ok.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(bullish_flip.iloc[i]) and bool(trend_ok.iloc[i]):
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
