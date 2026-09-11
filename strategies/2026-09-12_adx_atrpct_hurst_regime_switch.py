"""Strategy: ADX / ATR-percentile / Hurst-exponent 3-filter regime-switch
(momentum EMA-crossover in trending regime, z-score mean-reversion in
reverting regime, flat in the "no-regime" zone).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-136):
Per https://fortraders.com/blog/momentum-vs-mean-reversion-strategies-for-challenges
(Marcel Hambalek, For Traders, 2026-09-02), three measurable filters --
ADX(14), a rolling ATR percentile, and a rolling Hurst exponent -- jointly
classify the market's regime, and each strategy family (momentum/trend vs
mean-reversion) should ONLY be run inside its own regime:
    Momentum mode:       ADX > 25  AND ATR-pct > 60th  AND Hurst > 0.55
    Mean-reversion mode:  ADX < 20  AND ATR-pct < 40th  AND Hurst < 0.45
    No-regime zone (any other combination): flat, trade neither.

This repo has separately tested a rolling Hurst-exponent gate on its own
(2026-09-04-155/156, both rejected -- single-filter Hurst alone was too
noisy/whipsaw-prone) and ADX/ATR-percentile regime filters individually in
various other strategies, but never this specific THREE-WAY joint filter
(ADX confirms trend strength, ATR-percentile confirms there is enough range
expansion to pay for continuation/reversion risk, Hurst confirms the series
isn't just noise) driving a genuinely bimodal strategy that switches between
trend-following (EMA 12/26 crossover) and mean-reversion (20d z-score fade)
depending on which regime is active, with an explicit "trade neither" dead
zone when the three filters disagree. This is architecturally distinct from
any prior single-indicator Hurst/ADX/ATR strategy in this repo.

Signal logic
------------
- ADX(14): standard Wilder ADX.
- ATR percentile: rolling ATR(14), then its percentile rank within a
  trailing 100-bar window (0-100).
- Hurst exponent: rolling R/S-analysis estimate over a trailing window
  (same estimator as 2026-09-04-155/156's rejected single-filter version,
  reused here purely as one of three joint filters).
- Momentum mode active when ADX > adx_trend_th AND atr_pct > atr_trend_pct
  AND hurst > hurst_trend_th: long when EMA(fast) > EMA(slow), flat
  otherwise (classic crossover trigger, but gated to fire only in this
  regime).
- Mean-reversion mode active when ADX < adx_mr_th AND atr_pct < atr_mr_pct
  AND hurst < hurst_mr_th: long when the z-score of close vs its own
  rolling SMA/STD is below -entry_z (oversold), exit when z reverts to >=
  0 or after max_hold_days.
- No-regime zone (neither condition holds): flat.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1}
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wilder_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = pd.concat(
        [
            (high - low),
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(
        alpha=1.0 / period, adjust=False, min_periods=period
    ).mean() / atr.replace(0, np.nan)
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(
        alpha=1.0 / period, adjust=False, min_periods=period
    ).mean() / atr.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    return adx


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat(
        [
            (high - low),
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _rolling_hurst(close: pd.Series, window: int = 100) -> pd.Series:
    """Rolling R/S-analysis Hurst exponent estimate (single-lag proxy,
    consistent with this repo's prior 2026-09-04-155/156 estimator)."""
    log_ret = np.log(close / close.shift(1))

    def _hurst_of_window(x: np.ndarray) -> float:
        x = x[~np.isnan(x)]
        n = len(x)
        if n < 20:
            return np.nan
        mean_adj = x - x.mean()
        cum_dev = np.cumsum(mean_adj)
        r = cum_dev.max() - cum_dev.min()
        s = x.std()
        if s == 0 or r == 0:
            return np.nan
        rs = r / s
        return float(np.log(rs) / np.log(n))

    return log_ret.rolling(window).apply(_hurst_of_window, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    adx_period: int = 14,
    atr_period: int = 14,
    atr_pct_window: int = 100,
    hurst_window: int = 100,
    adx_trend_th: float = 25.0,
    atr_trend_pct: float = 60.0,
    hurst_trend_th: float = 0.55,
    adx_mr_th: float = 20.0,
    atr_mr_pct: float = 40.0,
    hurst_mr_th: float = 0.45,
    ema_fast: int = 12,
    ema_slow: int = 26,
    zscore_window: int = 20,
    entry_z: float = 1.5,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    adx = _wilder_adx(df, adx_period)
    atr = _atr(df, atr_period)
    atr_pct = atr.rolling(atr_pct_window).apply(
        lambda x: 100.0 * (x < x[-1]).sum() / len(x), raw=True
    )
    hurst = _rolling_hurst(close, hurst_window)

    momentum_regime = (
        (adx > adx_trend_th) & (atr_pct > atr_trend_pct) & (hurst > hurst_trend_th)
    ).fillna(False)
    mr_regime = (
        (adx < adx_mr_th) & (atr_pct < atr_mr_pct) & (hurst < hurst_mr_th)
    ).fillna(False)

    ema_f = close.ewm(span=ema_fast, adjust=False).mean()
    ema_s = close.ewm(span=ema_slow, adjust=False).mean()
    ema_bull = ema_f > ema_s

    sma = close.rolling(zscore_window).mean()
    std = close.rolling(zscore_window).std()
    zscore = (close - sma) / std.replace(0, np.nan)
    mr_entry = zscore < -entry_z
    mr_exit = zscore >= 0

    position = pd.Series(0, index=close.index, dtype=int)
    in_mr_position = False
    mr_entry_idx = 0

    for i in range(len(close)):
        if bool(momentum_regime.iloc[i]):
            in_mr_position = False
            position.iloc[i] = 1 if bool(ema_bull.iloc[i]) else 0
        elif bool(mr_regime.iloc[i]):
            if in_mr_position:
                held = i - mr_entry_idx
                if bool(mr_exit.iloc[i]) or held >= max_hold_days:
                    in_mr_position = False
                    position.iloc[i] = 0
                else:
                    position.iloc[i] = 1
            else:
                if bool(mr_entry.iloc[i]):
                    in_mr_position = True
                    mr_entry_idx = i
                    position.iloc[i] = 1
                else:
                    position.iloc[i] = 0
        else:
            # no-regime zone: trade neither, flatten
            in_mr_position = False
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
