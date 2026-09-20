"""Strategy: TrendSpider Volatility Regime Classifier (VRC) composite gate
on SMA trend-following.

Source: https://trendspider.com (Volatility Regime Classifier indicator
page, read via browser_exec this iteration after web_search's DDGS backend
returned a generic AI-overview summary but not the direct article text --
confirmed via Google SERP + AI-overview snippet, cross-checked against
multiple trendspider.com store-page listings of the same VRC spec).

Per the source: "The VRC creates a composite of three volatility
estimators: Parkinson (20% weight), Garman-Klass (30% weight), Yang-Zhang
(50% weight)," normalized into "Volatility Bands... aligned as +-2 standard
deviations" and a "Z-Score view: phase contextualization via
distance-to-mean," with an information panel showing a "Volatility State:
expanding / contracting / normal."

Hypothesis
----------
Each of Parkinson, Garman-Klass, and Yang-Zhang range/gap-based volatility
estimators has already been tested individually in this repo as a
volatility-regime gate (ids referenced in strategies_index.jsonl), all
rejected or near-miss. TrendSpider's specific weighted-composite
construction (20/30/50%) is a genuinely different, previously-untested
signal: Yang-Zhang gets the dominant weight because it is the only one of
the three that incorporates the overnight (close-to-open) gap component,
so the composite should react faster to overnight-driven volatility shifts
than any single estimator alone. This strategy gates a fast/slow SMA
trend-following crossover to only trade when the VRC composite's rolling
Z-score is BELOW an upper-bound threshold (i.e. we are NOT already in an
"expanding"/high volatility-of-volatility regime that has structurally
hurt trend-following elsewhere in this repo), on the theory that a
composite measure -- being less noisy than any single estimator -- should
produce a cleaner regime split than the single-estimator gates already
rejected.

Signal logic
------------
- Parkinson variance (per bar): (1/(4*ln2)) * ln(high/low)^2
- Garman-Klass variance (per bar): 0.5*ln(high/low)^2 -
  (2*ln2-1)*ln(close/open)^2
- Yang-Zhang variance (per bar, simplified rolling form): overnight
  variance (ln(open/prev_close))^2 plus a k-weighted blend of open-to-close
  variance and the Rogers-Satchell term (k=0.34/(1.34+(n+1)/(n-1)) per
  Yang-Zhang's own paper, using n=vrc_window).
- Each per-bar variance series is rolled over `vrc_window` days (mean),
  annualized (x252), then sqrt'd to get a volatility level; composite VRC =
  0.2*Parkinson_vol + 0.3*GarmanKlass_vol + 0.5*YangZhang_vol.
- VRC Z-score = (VRC - rolling_mean(VRC, vrc_window)) /
  rolling_std(VRC, vrc_window), both computed on PRIOR bars (shifted 1) to
  avoid look-ahead.
- Entry (long): fast SMA (`fast_window`) crosses above slow SMA
  (`slow_window`) AND VRC Z-score <= `z_upper_bound` (not already in an
  expanding-volatility regime).
- Exit: fast SMA crosses back below slow SMA, OR VRC Z-score exceeds
  `z_upper_bound` (regime flips to expanding -- risk-off exit), OR a
  max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def _vrc_composite(df: pd.DataFrame, vrc_window: int) -> pd.Series:
    """Compute the TrendSpider-style VRC composite volatility level series."""
    high, low, close, open_ = df["high"], df["low"], df["close"], df["open"]
    prev_close = close.shift(1)

    log_hl = np.log(high / low)
    log_co = np.log(close / open_)
    log_oc_prev = np.log(open_ / prev_close)
    log_ho = np.log(high / open_)
    log_lo = np.log(low / open_)

    # Parkinson per-bar variance.
    parkinson_var = (1.0 / (4.0 * np.log(2.0))) * (log_hl ** 2)

    # Garman-Klass per-bar variance.
    gk_var = 0.5 * (log_hl ** 2) - (2.0 * np.log(2.0) - 1.0) * (log_co ** 2)

    # Rogers-Satchell per-bar variance (drift-independent), used inside
    # Yang-Zhang.
    rs_var = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)

    n = vrc_window
    k = 0.34 / (1.34 + (n + 1) / max(n - 1, 1))

    overnight_var = (log_oc_prev - log_oc_prev.rolling(n).mean()) ** 2
    open_close_var = (log_co - log_co.rolling(n).mean()) ** 2

    overnight_roll = overnight_var.rolling(n).mean()
    open_close_roll = open_close_var.rolling(n).mean()
    rs_roll = rs_var.rolling(n).mean()

    yz_var = overnight_roll + k * open_close_roll + (1 - k) * rs_roll

    parkinson_vol = np.sqrt((parkinson_var.rolling(n).mean() * 252).clip(lower=0))
    gk_vol = np.sqrt((gk_var.rolling(n).mean() * 252).clip(lower=0))
    yz_vol = np.sqrt((yz_var * 252).clip(lower=0))

    vrc = 0.2 * parkinson_vol + 0.3 * gk_vol + 0.5 * yz_vol
    return vrc


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 50,
    vrc_window: int = 20,
    z_upper_bound: float = 1.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    vrc = _vrc_composite(df, vrc_window)
    vrc_mean = vrc.rolling(vrc_window).mean().shift(1)
    vrc_std = vrc.rolling(vrc_window).std().shift(1)
    vrc_z = (vrc.shift(1) - vrc_mean) / vrc_std.replace(0, pd.NA)

    fast_sma = close.rolling(fast_window).mean()
    slow_sma = close.rolling(slow_window).mean()

    bullish_cross = (fast_sma > slow_sma) & (fast_sma.shift(1) <= slow_sma.shift(1))
    bearish_cross = (fast_sma < slow_sma) & (fast_sma.shift(1) >= slow_sma.shift(1))
    calm_regime = (vrc_z <= z_upper_bound).fillna(False)

    entry = bullish_cross.fillna(False) & calm_regime
    exit_cross = bearish_cross.fillna(False)
    exit_regime = ~calm_regime

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or bool(exit_regime.iloc[i]) or held >= max_hold_days:
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
