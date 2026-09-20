"""Strategy: Corwin-Schultz high-low bid-ask spread estimator as a liquidity
regime filter, gating an SMA trend-following long entry.

Hypothesis (see knowledge_base/strategies_log.jsonl, this entry's id):
Per Corwin & Schultz (2012, Journal of Finance) "A Simple Way to Estimate
Bid-Ask Spreads from Daily High and Low Prices" -- read via
thefintechbuilder.com's worked-example explainer (https://thefintechbuilder.com/market-microstructure/liquidity-and-spreads/corwin-schultz-spread-estimator/,
plus conceptual background from https://quantmemo.com/concepts/corwin-schultz-high-low-spread,
after web_search's DDGS backend TLS-erroring on the initial follow-up
query) -- the CS estimator recovers an approximate effective bid-ask spread
from nothing but consecutive daily high/low prices, exploiting the fact
that true price volatility scales with sqrt(time) while the bid-ask-bounce
component of the observed high-low range does not. A widening estimated
spread (rising CS) signals deteriorating liquidity/rising trading friction
-- often coincident with market stress -- while a narrow/tight estimated
spread signals calm, liquid conditions more conducive to trend persistence.

This strategy uses the CS spread as a liquidity regime FILTER: only take a
standard SMA(fast)>SMA(slow) trend-following long entry when the rolling CS
spread estimate is below its own recent rolling percentile (calm/liquid
regime), and exit if the spread estimate spikes above that percentile
(liquidity deteriorating) in addition to the standard trend-reversal exit.
First Corwin-Schultz-based strategy in this repo (0 prior "corwin schultz"
hits in strategies_index.jsonl) -- a genuinely different construction from
this repo's other liquidity/microstructure proxies (Amihud illiquidity is
volume-based; Roll measure is serial-covariance-based; CS uses only
high/low ranges via a volatility-scaling argument).

Signal logic
------------
- Corwin-Schultz two-day spread estimator (standard formula, clipped at
  zero):
    beta_t   = ln(H_t/L_t)^2 + ln(H_{t+1}/L_{t+1})^2
    gamma_t  = ln(max(H_t,H_{t+1}) / min(L_t,L_{t+1}))^2
    k        = 3 - 2*sqrt(2)
    alpha_t  = (sqrt(2*beta_t) - sqrt(beta_t)) / k - sqrt(gamma_t / k)
    S_t      = 2*(exp(alpha_t) - 1) / (1 + exp(alpha_t)), clipped to >= 0
  (S_t is a same-day relative-spread estimate anchored on the 2-day window
  ending at t+1; assigned to date t+1 per the paper's own indexing.)
- Rolling liquidity regime: S_t's rolling `spread_pctile_window`-day
  percentile rank; "calm" when current S_t is below its own trailing
  `spread_pctile_threshold` percentile (e.g. 50th).
- Entry (long): SMA(fast) > SMA(slow) (uptrend) AND liquidity regime calm
  (S_t below its own rolling percentile threshold).
- Exit: SMA(fast) crosses back below SMA(slow), OR liquidity regime turns
  stressed (S_t rises above its own rolling percentile threshold), OR
  max_hold_days elapses (safety backstop).

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _corwin_schultz_spread(high: pd.Series, low: pd.Series) -> pd.Series:
    """Corwin-Schultz (2012) two-day high-low spread estimator, clipped
    at zero, indexed to the SECOND day of each overlapping 2-day window."""
    k = 3.0 - 2.0 * np.sqrt(2.0)

    h1, l1 = high, low
    h2, l2 = high.shift(1), low.shift(1)

    beta = (np.log(h1 / l1)) ** 2 + (np.log(h2 / l2)) ** 2
    two_day_high = pd.concat([h1, h2], axis=1).max(axis=1)
    two_day_low = pd.concat([l1, l2], axis=1).min(axis=1)
    gamma = (np.log(two_day_high / two_day_low)) ** 2

    alpha = (np.sqrt(2.0 * beta) - np.sqrt(beta)) / k - np.sqrt(gamma / k)
    spread = 2.0 * (np.exp(alpha) - 1.0) / (1.0 + np.exp(alpha))
    spread = spread.clip(lower=0.0)
    return spread


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 50,
    spread_pctile_window: int = 120,
    spread_pctile_threshold: float = 0.5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    sma_fast = close.rolling(fast_window).mean()
    sma_slow = close.rolling(slow_window).mean()
    trend_up = sma_fast > sma_slow

    spread = _corwin_schultz_spread(high, low)
    spread_pctile = spread.rolling(spread_pctile_window).apply(
        lambda w: pd.Series(w).rank(pct=True).iloc[-1] if len(w) > 1 else np.nan,
        raw=False,
    )
    calm_regime = spread_pctile < spread_pctile_threshold

    entry = trend_up & calm_regime
    exit_signal = (~trend_up) | (~calm_regime)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_arr = entry.fillna(False).values
    exit_arr = exit_signal.fillna(True).values
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_arr[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_arr[i]):
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
