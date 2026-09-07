"""Strategy: Percentage-distance-from-moving-average mean reversion, gated by
an ADX ranging-regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-002):
Per https://www.coinquant.ai/blog/building-a-mean-reversion-strategy-in-cryptocurrency-markets-evidence-from-78-backtests
("Strategy C: Percentage distance from moving average" -- entry when price
is X% below its 20-period SMA, exit when price recovers to/above the SMA),
the source's own worked example and Section 4 regime-dependence analysis
found naive mean reversion (their BB(20,2) variant, same underlying
displacement-from-mean idea) lost -38.9%/-39.3% on BTC/ETH through the
trending 2022 bear market, while the source's Section 4.2 "simple regime
filter" explicitly proposes: only take mean-reversion entries when ADX(14)
is NOT above ~25 (i.e., market is ranging, not trending). This strategy
implements Strategy C (percentage distance from a moving average, the
easiest-to-read of their three displacement metrics) WITH that source's own
proposed ADX ranging-filter bolted on, rather than testing it naked as the
source's raw grid did. First percentage-distance-from-MA (BIAS-style)
strategy in this repo -- distinct from Bollinger Band z-score reversion
(2026-09-03-001, already tested/accepted for QQQ low-vol only) since this
uses a fixed percentage threshold instead of a volatility-normalized
z-score, and distinct from all prior ADX-gated strategies (e.g.
2026-09-04-162 BB+ADX>threshold, which required a STRONG trend; here ADX
must be BELOW threshold, i.e. the opposite/ranging condition).

Signal logic
------------
- 20-period SMA of close; pct_distance = (close - SMA) / SMA * 100.
- ADX(14) (Wilder) measures trend strength.
- Entry (long): pct_distance <= -entry_pct (price is entry_pct% or more
  below its SMA) AND ADX <= adx_max (market is NOT strongly trending, i.e.
  ranging/low-trend-strength condition per source's own regime filter).
- Exit: close crosses back at/above the SMA (mean-reversion target reached),
  OR ADX rises above adx_max (regime flips to trending -- risk-off exit per
  source's own worked 2022 bear-market caution), OR after max_hold_days
  time-stop (avoid indefinite holds through a bad regime read).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(0.0, index=high.index)
    minus_dm = pd.Series(0.0, index=high.index)
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[(down_move > up_move) & (down_move > 0)]

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = _wilder_smooth(tr, period)
    plus_dm_smooth = _wilder_smooth(plus_dm, period)
    minus_dm_smooth = _wilder_smooth(minus_dm, period)

    plus_di = 100.0 * (plus_dm_smooth / atr.replace(0, pd.NA))
    minus_di = 100.0 * (minus_dm_smooth / atr.replace(0, pd.NA))

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    adx = _wilder_smooth(dx.fillna(0.0), period)
    return adx.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    ma_window: int = 20,
    entry_pct: float = 5.0,
    adx_period: int = 14,
    adx_max: float = 25.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    sma = close.rolling(ma_window, min_periods=ma_window).mean()
    pct_distance = (close - sma) / sma * 100.0
    adx = _adx(high, low, close, adx_period)

    entry = (pct_distance <= -abs(entry_pct)) & (adx <= adx_max)
    entry = entry.fillna(False)

    trend_flip = adx > adx_max
    reverted = close >= sma

    n = len(df)
    entry_arr = entry.to_numpy()
    reverted_arr = reverted.to_numpy()
    trend_flip_arr = trend_flip.to_numpy()
    pos_arr = [0] * n

    in_pos = False
    hold_counter = 0
    for i in range(n):
        if in_pos:
            hold_counter += 1
            exit_now = bool(reverted_arr[i]) or bool(trend_flip_arr[i]) or hold_counter >= max_hold_days
            if exit_now:
                in_pos = False
                hold_counter = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if bool(entry_arr[i]):
                in_pos = True
                hold_counter = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    ma_window: int = 20,
    entry_pct: float = 5.0,
    adx_period: int = 14,
    adx_max: float = 25.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        ma_window=ma_window,
        entry_pct=entry_pct,
        adx_period=adx_period,
        adx_max=adx_max,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
