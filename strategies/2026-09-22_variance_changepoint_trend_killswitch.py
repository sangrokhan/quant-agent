"""Strategy: SMA-trend following gated by a simplified Bayesian-style
variance-changepoint "kill switch".

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-002):
Per quantbeckman.com's "[WITH CODE] Switch-Off: Bayesian online changepoint
detection" (https://www.quantbeckman.com/p/with-code-switch-off-bayesian-online),
the core idea for de-allocating a strategy is to distinguish "stochastic
noise" (a normal adverse-variance excursion, keep trading) from "structural
decay" (the return-generating process itself has shifted, e.g. variance has
jumped to a new regime -- stop trading) using a probabilistic run-length/
changepoint framework on the return series, rather than a naive fixed
drawdown stop. The article's full Bayesian online changepoint detection
(BOCPD) machinery (Student-t predictive likelihood, log-space recursive
run-length posterior, hazard-rate prior) is not reimplementable within one
loop iteration without a dedicated library, so this strategy implements a
simplified, practically-equivalent proxy: a two-window realized-variance
ratio test (short-window variance vs long-window variance, z-scored against
its own trailing history) as the "changepoint" trigger. When the ratio
z-score exceeds a threshold (short-term variance has spiked well above its
recent normal relationship to long-term variance), that is treated as
evidence of a structural regime shift and the strategy goes flat
(kill-switch), overriding the base trend signal, until the variance ratio
normalizes again.

Distinct from this repo's existing CUSUM entries (which flag a MEAN/drift
event to trigger a NEW entry) and existing volatility_regime_filter/tercile
strategies (which gate on absolute vol level) -- here the trigger is a
RELATIVE variance-ratio changepoint (short vs long variance diverging from
their own historical relationship), applied as an OVERRIDE kill-switch on
top of a simple SMA trend-following base signal, mirroring the source's own
"de-allocation on top of an existing strategy" framing rather than being
the base signal itself.

Signal logic
------------
- Base trend signal: long when close > SMA(trend_window), flat otherwise.
- Realized variance: `short_window`-day and `long_window`-day rolling
  variance of daily log returns.
- Variance ratio: short_var / long_var.
- Changepoint flag: variance ratio z-scored against its own trailing
  `zscore_lookback`-day history; changepoint triggers (kill-switch ON) when
  z-score >= `cp_threshold`.
- Position: base trend signal AND NOT in kill-switch state. Once triggered,
  kill-switch stays on for `cooldown_days` trading days (a full BOCPD would
  probabilistically decay the "changepoint just happened" belief; this is a
  simple fixed-cooldown proxy for that decay) before the base trend signal
  can resume.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1}
    generate_returns(price_df, **params) -> pd.Series daily strategy returns
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
    trend_window: int = 50,
    short_window: int = 10,
    long_window: int = 60,
    zscore_lookback: int = 252,
    cp_threshold: float = 2.0,
    cooldown_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series: SMA trend-following,
    overridden to flat by a variance-ratio changepoint kill-switch."""
    df = _prep(price_df)
    close = df["close"]

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)

    short_var = daily_log_ret.rolling(short_window).var()
    long_var = daily_log_ret.rolling(long_window).var()
    var_ratio = short_var / long_var.replace(0, pd.NA)

    ratio_mean = var_ratio.rolling(zscore_lookback, min_periods=long_window).mean()
    ratio_std = var_ratio.rolling(zscore_lookback, min_periods=long_window).std()
    ratio_z = (var_ratio - ratio_mean) / ratio_std.replace(0, pd.NA)

    changepoint_event = (ratio_z >= cp_threshold).fillna(False)

    sma = close.rolling(trend_window).mean()
    trend_long = (close > sma).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    cooldown_remaining = 0
    for i in range(len(close)):
        if bool(changepoint_event.iloc[i]):
            cooldown_remaining = cooldown_days
        if cooldown_remaining > 0:
            position.iloc[i] = 0
            cooldown_remaining -= 1
        else:
            position.iloc[i] = 1 if bool(trend_long.iloc[i]) else 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
