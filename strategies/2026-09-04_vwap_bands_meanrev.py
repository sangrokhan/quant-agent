"""Strategy: Rolling volume-weighted VWAP standard-deviation bands mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-052):
Source: https://fazencapital.com/learn/en/vwap-standard-deviation-bands
(fetched via browser_exec after web_search failed with the recurring
DDGS/Yahoo TLS connection error).

The source describes intraday session VWAP standard-deviation bands: the mean
is the volume-weighted average price (not a simple price average), and the
dispersion band is also volume-weighted:
    sigma = sqrt( sum(volume_i * (price_i - VWAP)^2) / sum(volume_i) )
Bands are plotted at VWAP +/- n*sigma (n=1 captures ~68% of volume, n=2
~95% under a normality assumption). The source explicitly warns: (a) a band
touch alone is a losing signal on trend days (price can ride the band), and
(b) mean-reversion setups should be gated to non-trending conditions.

This repo trades daily bars (no intraday session), so this strategy adapts
the concept to a rolling N-day volume-weighted VWAP + volume-weighted sigma
(no session reset -- a continuously rolling analog), and reuses this repo's
established vol-regime-gate pattern (2026-09-03-001) as the closest
implementable proxy for the source's "trend day" filter: only take the
mean-reversion entry when trailing realized volatility is NOT elevated
(i.e., avoid entering VWAP-band-touch fades during high-vol/trending
regimes, matching the source's own caveat).

Signal logic
------------
- Rolling VWAP over `vwap_window` days: sum(close*volume)/sum(volume).
- Rolling volume-weighted sigma over the same window per the source formula.
- Lower band = VWAP - band_std * sigma.
- Realized vol regime: 20-day realized vol (annualized) vs its trailing
  252-day median; "low/normal vol" when current <= vol_regime_ratio * median
  (elevated/trend-day proxy is the complement).
- Entry (long): close crosses below the lower VWAP band AND NOT in an
  elevated-vol regime (source's trend-day exclusion).
- Exit: close crosses back above the rolling VWAP (mean-reversion target),
  OR the vol regime flips to elevated (risk-off / trend-day starting),
  OR after `max_hold_days` (avoid indefinite holds, consistent with this
  repo's other mean-reversion strategies e.g. 2026-09-03_bb_meanrev).

Interface contract for validators (see validation/validators.py and
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def generate_signals(
    price_df: pd.DataFrame,
    vwap_window: int = 20,
    band_std: float = 2.0,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"].astype(float)

    # Rolling volume-weighted VWAP.
    pv = close * volume
    rolling_vol_sum = volume.rolling(vwap_window).sum()
    vwap = pv.rolling(vwap_window).sum() / rolling_vol_sum

    # Rolling volume-weighted sigma: sqrt(sum(vol*(price-vwap)^2)/sum(vol)).
    # Use the *current* rolling vwap (recomputed each window end) as the
    # reference mean per the source's own-session formula.
    sq_dev_weighted = (volume * (close - vwap) ** 2).rolling(vwap_window).sum()
    sigma = (sq_dev_weighted / rolling_vol_sum) ** 0.5

    lower_band = vwap - band_std * sigma

    # Realized-vol regime filter (proxy for source's "trend day" exclusion).
    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    normal_vol_regime = realized_vol <= (vol_median_1y * vol_regime_ratio)

    entry = (close < lower_band) & normal_vol_regime.fillna(False)
    exit_meanrev = close > vwap
    exit_regime_flip = ~normal_vol_regime.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
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
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
