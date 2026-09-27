"""Strategy: SMA trend-following gated ON only during statistically
significant ATR-exceedance-frequency volatility expansion.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per LuxAlgo's "ATR Exceedance Probability Model" (VEPM) indicator
(https://www.luxalgo.com/library/indicator/atr-exceedance-probability-model/,
published 19 May 2026, read via browser_exec this iteration -- web_search
DDGS backend returned no results for this specific query), the indicator's
own disclosed mechanism is:

1. A "breach" event fires on any bar whose (high-low) range exceeds
   atr_multiplier * ATR(atr_length).
2. The SHORT-TERM breach frequency (fraction of breach bars over the last
   short_window bars) is compared against a LONG-TERM baseline breach
   frequency (fraction of breach bars over the last baseline_window bars,
   200 by default).
3. This frequency delta is Z-scored (using the binomial standard error of
   the baseline frequency over a sample of short_window bars) to test
   whether the recent breach rate is a STATISTICALLY SIGNIFICANT deviation
   from the long-run norm ("Z-Score Sensitivity" setting) -- this is what
   the source calls testing whether elevated/depressed breach frequency
   "clears a significance bar", grounded in volatility clustering (active
   stretches tend to follow active stretches).
4. Source's own trading guidance ("How to Trade" section): a "green
   significant glow" (Z-score clears the positive sensitivity threshold --
   breach frequency statistically ABOVE baseline) "supports breakout and
   continuation ideas"; a "red shift" (breach frequency below baseline)
   "signals contraction, weaker momentum, or a quieter regime suited to
   patience."

This iteration operationalizes that exact guidance as a volatility-regime
GATE on a plain SMA trend-following signal (long-standing baseline pattern
in this repo, e.g. 2026-09-03_momentum_trend200_filter.py): the SMA trend
signal is only allowed to be long when the VEPM Z-score is significantly
positive (statistically-confirmed volatility EXPANSION, i.e. active
breakout/continuation regime per the source's own framing); flat during
low-significance or contraction regimes. This is a genuinely novel angle
distinct from every prior ATR/volatility-regime strategy in this repo
(none of which used an exceedance-FREQUENCY Z-score gate -- prior variants
used raw ATR percentile, realized-vol percentile, or ATR-expansion-ratio
gates directly on the ATR level, not on the statistical significance of
its breach RATE against a rolling baseline).

Signal logic
------------
- ATR(atr_length) via Wilder's smoothing (EMA-style running average of
  True Range).
- breach[t] = 1 if (high[t]-low[t]) > atr_multiplier * ATR[t] else 0.
- short_freq[t] = mean(breach) over trailing short_window bars.
- baseline_freq[t] = mean(breach) over trailing baseline_window bars.
- Binomial standard error of baseline_freq over a short_window-bar sample:
  se[t] = sqrt(baseline_freq[t] * (1 - baseline_freq[t]) / short_window),
  floored at a small epsilon to avoid division by zero.
- z[t] = (short_freq[t] - baseline_freq[t]) / se[t].
- Volatility-expansion regime: z[t] >= z_threshold (significant, positive
  per source's "green significant glow" framing).
- Trend signal: close[t] > SMA(sma_window)[t].
- Position: long (1) iff trend signal is up AND in an expansion regime;
  flat otherwise. No shorting.

Source read this iteration:
- https://www.luxalgo.com/library/indicator/atr-exceedance-probability-model/
  (LuxAlgo, published 19 May 2026 -- full mechanical description of the
  breach/frequency/Z-score construction and the source's own directional
  trading interpretation of the Z-score sign, read via browser_exec after
  web_search returned no results for "ATR exceedance probability trading
  strategy").

First ATR-exceedance-frequency-Z-score-family strategy in this repo (KB
search for "ATR Exceedance"/"Serial Break Probability"/"exceedance
probability" returned zero matches in strategies_index.jsonl).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept the strategy's tunable parameters as kwargs.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, atr_length: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    # Wilder's smoothing (equivalent to an EMA with alpha=1/atr_length).
    atr = tr.ewm(alpha=1.0 / atr_length, adjust=False, min_periods=atr_length).mean()
    return atr


def _vepm_zscore(
    df: pd.DataFrame,
    atr_length: int,
    atr_multiplier: float,
    short_window: int,
    baseline_window: int,
) -> pd.Series:
    high = df["high"]
    low = df["low"]
    atr = _atr(df, atr_length)

    breach = ((high - low) > (atr_multiplier * atr)).astype(float)

    short_freq = breach.rolling(short_window, min_periods=short_window).mean()
    baseline_freq = breach.rolling(baseline_window, min_periods=baseline_window).mean()

    eps = 1e-6
    se = ((baseline_freq * (1.0 - baseline_freq)).clip(lower=0.0) / short_window).pow(0.5)
    se = se.clip(lower=eps)

    z = (short_freq - baseline_freq) / se
    return z


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 100,
    atr_length: int = 14,
    atr_multiplier: float = 1.0,
    short_window: int = 20,
    baseline_window: int = 200,
    z_threshold: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(sma_window, min_periods=sma_window).mean()
    trend_up = close > sma

    z = _vepm_zscore(df, atr_length, atr_multiplier, short_window, baseline_window)
    expansion_regime = z >= z_threshold

    position = (trend_up.fillna(False) & expansion_regime.fillna(False)).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    sma_window: int = 100,
    atr_length: int = 14,
    atr_multiplier: float = 1.0,
    short_window: int = 20,
    baseline_window: int = 200,
    z_threshold: float = 1.0,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        sma_window=sma_window,
        atr_length=atr_length,
        atr_multiplier=atr_multiplier,
        short_window=short_window,
        baseline_window=baseline_window,
        z_threshold=z_threshold,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
