# Backtest Report: Gaussian Channel Trend-Breakout

**Strategy file:** `strategies/2026-09-06_gaussian_channel_breakout.py`
**Date:** 2026-09-06

## Hypothesis

The Gaussian Channel (an IIR/bell-curve-weighted low-lag smoothing filter,
per DonovanWall's open-source "Gaussian Channel (DW)" indicator) produces a
smoothed midline plus volatility-scaled upper/lower bands. Per the
"TRADLEWARE - Gaussian Channel + Stochastic RSI" community strategy write-up
(https://kr.tradingview.com/scripts/gaussianchannel), long entries fire when
the channel midline is rising ("green") AND price closes above the upper
band (trend-confirmed breakout); exits fire when price closes back below
the upper band OR the channel flips from green to red. This repo tests a
simplified version (dropping the source's Stochastic RSI and bullish-candle
micro-filters, kept out of scope for a first test) retaining the core
channel-color + band-breakout entry/exit and the 200-day SMA bull-regime
gate, plus a max_hold_days=30 time-stop backstop.

Source parameters used: Poles=4, Sampling Period=144 (per the
kr.tradingview.com "baseline version" description and multiple corroborating
SERP snippets), True Range Multiplier tested at 1.0/1.414/2.0 (1.414
suggested by a Scribd "Gaussian Channel Strategy v3.0" reference, not
independently confirmed).

## Sources

- https://kr.tradingview.com/scripts/gaussianchannel (primary — entry/exit rules, parameters)
- https://www.quantum-algo.com/blog/guides/gaussian-channel-indicator-complete-guide/ (background/conceptual)
- Google SERP snippets for "Gaussian Channel indicator default settings poles 144 multiplier" (parameter corroboration: FMZQuant, ProRealCode, useThinkScript)

## Implementation note

This repo has no true recursive N-pole Gaussian IIR filter available, so
`poles` is approximated by `poles` successive passes of an EMA with
span=sampling_period — a standard practical approximation of a multi-pole
low-pass filter chain (each additional pass increases smoothness/lag
similarly to how the source describes poles behaving). This is a
documented approximation, not the exact DonovanWall recursive formula.

## Step 6 — Grid test summary

Grid: `sampling_period` in [89, 144] x `tr_mult` in [1.0, 1.414, 2.0] x
`trend_window`=200 x `max_hold_days`=30, on QQQ+SPY (equity) and
BTC/USDT+ETH/USDT (crypto), vol_regime_splits=3, 2015-01-01 to 2026-09-01.

- **Total cells:** 72, **passed:** 18, **pass_fraction: 0.25**
- **By asset class:** equity 18/36 (50%), crypto 0/36 (0%)
- **By vol regime:** low 12/24 (50%), mid 6/24 (25%), high 0/24 (0%)
- **Best cell:** sampling_period=144, tr_mult=1.0, trend_window=200,
  max_hold_days=30 — SPY, low-vol regime, Sharpe 2.468
- **Worst cell:** sampling_period=89, tr_mult=1.0 — SPY, high-vol regime,
  Sharpe -0.414

The strategy shows a real (non-trivial) equity edge concentrated in
low/mid-vol regimes, but categorically fails on crypto (0/36) — consistent
with the source's own framing that this is a daily-timeframe, medium-term
trend tool (validated by the source specifically on ETH/USDT with a
*faster* sampling_period=89 config, which this repo's crypto test used as
one of its two sampling_period values and still saw 0 passes, suggesting
crypto underperformance isn't just a parameter-scaling artifact).

## Step 7 — Single-config validation (best grid cell: sampling_period=144, tr_mult=1.0, trend_window=200, max_hold_days=30)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.841 (FAIL) | 0.578 (FAIL) | >= 1.0 |
| Max drawdown | 0.256 (FAIL) | 0.211 (PASS) | <= 0.25 |
| TC survival (10bps/trade) | 0.792 (PASS, 61 trades) | 0.515 (PASS, 63 trades) | >= 0.5 |
| Walk-forward | skipped (tooling bug) | skipped (tooling bug) | >= 0.75 |
| Parameter sensitivity | see grid: pass_fraction 0.25 across 12-cell param sweep, highly regime-concentrated | | <= 0.5 relative std |

Walk-forward skipped: `check_walk_forward` raises
`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'` in
the installed vectorbt version — a pre-existing repo-wide tooling bug also
noted in the 2026-09-06 Fibonacci-Bollinger-Bands entry, not specific to
this strategy.

## Step 8 — Decision: REJECTED

Both QQQ (0.841) and SPY (0.578) miss the full-sample Sharpe >= 1.0
threshold at the grid's own best-performing config. QQQ is a near-miss but
additionally fails max drawdown (0.256 vs 0.25, essentially at the
boundary). SPY misses decisively. The grid's headline positive result
(pass_fraction 0.25, best-cell Sharpe 2.468) is concentrated specifically
in low/mid-vol equity regimes and does not survive averaging into a
full-sample single-config Sharpe — the same "regime-concentrated result
looks great in slices, fails whole-sample" pattern seen repeatedly in this
repo's prior rejected entries (e.g. Fibonacci Bollinger Bands,
Acceleration Bands). Kept as a record of a rejected attempt.

## Future-revisit note

Given the strong low-vol-regime concentration (12/24 low-vol passes vs
0/24 high-vol), a future iteration could test an explicit low-vol-regime
gate on top of this same channel-breakout logic (mirroring the already-
accepted plain Bollinger Band mean-reversion strategy's low-vol gate
pattern) rather than relying only on the 200-SMA bull-regime filter, which
does not distinguish low-vol trending conditions from high-vol trending
ones.
