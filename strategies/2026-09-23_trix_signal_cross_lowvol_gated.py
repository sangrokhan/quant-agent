"""Strategy: TRIX signal-line crossover + EMA trend regime, EXPLICITLY
gated to only trade within the low realized-volatility tercile (vs.
2026-09-23-031's post-hoc observation that low-vol cells did well).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-032):
Direct follow-up to this cron trigger's own 2026-09-23-031 (TRIX(14)
signal-line(9/12) crossover + 50/200 EMA trend filter, near-missed
full-period Sharpe on SPY at 0.983 vs threshold 1.0). That iteration's grid
test showed an 0.875 pass rate specifically within the low realized-vol
tercile (vs 0.125 in mid/high combined) -- suggesting the unconditional
full-period average is diluted by whipsaw during higher-vol regimes. This
iteration bakes that observation directly into the entry rule (an explicit
low-vol regime GATE on ENTRY, not just a post-hoc breakdown), following the
same "filter OUT the regime that dilutes the edge" pattern used successfully
by strategies/2026-09-03_bb_meanrev_qqq_volregime.py.

Signal logic
------------
- Same TRIX/signal-line crossover + 50/200 EMA trend filter as
  2026-09-23-031.
- ADDITIONAL gate: 20-day realized volatility (annualized std of daily log
  returns) must be <= its trailing 252-day median (i.e. currently in a
  low/normal-vol regime) at the time of entry.
- Exit: TRIX crosses back below signal line, OR the vol regime flips to
  high-vol (risk-off exit, same mechanism as the BB meanrev reference
  strategy).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _trix(close: pd.Series, window: int) -> pd.Series:
    ema1 = close.ewm(span=window, adjust=False).mean()
    ema2 = ema1.ewm(span=window, adjust=False).mean()
    ema3 = ema2.ewm(span=window, adjust=False).mean()
    return ema3.pct_change() * 100


def generate_signals(
    price_df: pd.DataFrame,
    trix_window: int = 14,
    signal_window: int = 12,
    fast_ema: int = 50,
    slow_ema: int = 200,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    trix = _trix(close, trix_window)
    signal = trix.ewm(span=signal_window, adjust=False).mean()

    ema_fast = close.ewm(span=fast_ema, adjust=False).mean()
    ema_slow = close.ewm(span=slow_ema, adjust=False).mean()
    bullish_regime = (close > ema_fast) & (close > ema_slow)

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = realized_vol <= (vol_median_1y * vol_regime_ratio)

    golden_cross = (trix > signal) & (trix.shift(1) <= signal.shift(1))
    dead_cross = (trix < signal) & (trix.shift(1) >= signal.shift(1))

    entry = golden_cross & bullish_regime & low_vol_regime
    exit_ = dead_cross | (~low_vol_regime)

    pos_vals = []
    in_pos = False
    for i in range(len(close)):
        if not in_pos and bool(entry.iloc[i]):
            in_pos = True
        elif in_pos and bool(exit_.iloc[i]):
            in_pos = False
        pos_vals.append(1 if in_pos else 0)

    return pd.Series(pos_vals, index=close.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    trix_window: int = 14,
    signal_window: int = 12,
    fast_ema: int = 50,
    slow_ema: int = 200,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        trix_window=trix_window,
        signal_window=signal_window,
        fast_ema=fast_ema,
        slow_ema=slow_ema,
        vol_window=vol_window,
        vol_lookback=vol_lookback,
        vol_regime_ratio=vol_regime_ratio,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = (position.shift(1).fillna(0) * daily_ret).fillna(0.0)
    return strat_ret
