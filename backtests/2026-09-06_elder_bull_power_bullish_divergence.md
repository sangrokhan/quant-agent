# Elder-Ray Bull Power Bullish Divergence

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_elder_bull_power_bullish_divergence.py`
**KB id:** 2026-09-06-135

## Hypothesis

Per Capital.com's Elder-Ray explainer (which describes the bearish
mirror-case: "price makes a higher high, but bull power makes a lower
high" = fading buying pressure), this strategy tests the BULLISH
divergence analogue: price makes a lower low while Bull Power (High -
EMA13) makes a higher low, then entry on Bull Power crossing back above
zero. Distinct from the two prior Elder-Ray strategies in this repo
(2026-09-04-037, 2026-09-04-110), both of which use a simple
"Bear Power negative-but-rising" threshold, not a genuine two-swing-point
price-vs-indicator divergence.

**Source:** https://capital.com (Elder-ray indicator: bull power and bear
power, via Google SERP snippet, browser_exec) — bearish-divergence
definition mirrored for the bullish case tested here.

## Grid test (ema_window=[10,13,21] x swing_window=[3,5] x max_hold_days=[10,15], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 23/144 cells passed (equity 23/72, **crypto 0/72 decisively rejected**)
- By vol regime: low 6/48, mid 8/48, high 9/48 — spread across regimes,
  more promising-looking than most rejected strategies this run
- Best cell: ema_window=10, swing_window=5, max_hold_days=15, QQQ mid-vol,
  Sharpe 1.996

## Single-config validators (best grid config, full sample 2019-2026)

| Symbol | Full-sample Sharpe | Threshold |
|---|---|---|
| QQQ | 0.882 | ≥ 1.0 (FAIL) |
| SPY | 0.460 | ≥ 1.0 (FAIL) |

Max drawdown on QQQ: 7.9% (PASS, well within 25%). 110 trades on QQQ over
the full sample — enough for statistical relevance, but the per-vol-regime
cell Sharpe (1.996 in mid-vol) does not hold up once averaged across the
full sample, meaning the edge is concentrated in specific market
conditions rather than a robust, durable pattern.

## Decision: **REJECT**

Despite the highest grid pass_fraction of this run's iterations (16%,
spread across all three vol regimes on equity), full-sample Sharpe on
both QQQ (0.882) and SPY (0.460) misses the 1.0 threshold at the
grid's own best-performing config. This is a near-miss/regime-dependent
pattern worth flagging for a future loop to revisit with a regime filter
(e.g. gating entries to only the mid/high-vol terciles where the grid
cells actually passed) rather than trading it unconditionally as done
here. Skipped walk-forward/TC-survival/parameter-sensitivity given the
full-sample Sharpe miss on the primary config.
