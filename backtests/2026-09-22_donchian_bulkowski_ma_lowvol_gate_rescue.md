# Backtest Report: Donchian Breakout + Bulkowski MA Filter, Low-Vol-Regime-Gate Rescue Attempt

**Strategy file:** `strategies/2026-09-22_donchian_bulkowski_ma_lowvol_gate_rescue.py`
**Date:** 2026-09-22
**Outcome:** REJECTED (rescue failed -- Sharpe got worse, not better)

## Hypothesis

Rescue attempt for near-miss 2026-09-23-051 (Donchian breakout + Bulkowski
MA-position filter, best full-sample Sharpe 0.957 on QQQ, grid showed the
edge concentrated almost entirely in low-vol regime cells). Added an
explicit low-realized-vol-regime gate (20d realized vol <= vol_regime_ratio
x trailing 252d median, this repo's established construction) directly to
the entry condition, hypothesizing this would raise the full-sample Sharpe
above 1.0 by excluding the losing mid/high-vol trades.

## Primary config (QQQ, donchian_window=20, vol_regime_ratio=0.8)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.742 | >= 1.0 |
| Max drawdown | pass | 7.9% | <= 25% |
| TC survival | pass | 0.718 | >= 0.5 |
| Walk-forward | pass | 1.0 | >= 0.75 |
| Parameter sensitivity | pass | 0.017 rel. std | <= 0.5 |

Number of trades: 6 (down from 10 in the ungated version).

## Step 6 grid summary (72 cells: donchian_window in [20,40] x
vol_regime_ratio in [0.8,1.0,1.2] x {QQQ,SPY,BTC/USDT,ETH/USDT} x
low/mid/high vol tercile)

- Overall pass_fraction: 0.181 (13/72), marginally higher than the base
  strategy's 0.160, but this is misleading -- it comes from removing
  losing high/mid-vol cells from the denominator, not from making the
  low-vol cells any better.
- By vol regime: low 13/24 passed, mid 0/24, high 0/24 (same qualitative
  pattern as before -- gating just enforces what the grid already showed).
- Best cell unchanged: QQQ, donchian_window=20/vol_regime_ratio=0.8,
  low-vol, Sharpe 2.15 (vs 2.12 ungated -- negligible difference).

## Decision

REJECTED -- the rescue failed. Restricting the ENTRY condition itself to
the low-vol regime (rather than just observing that the strategy performs
best in low-vol slices) cut trade count from 10 to 6 and dropped
full-sample Sharpe from 0.957 to 0.742 -- the opposite of the intended
effect. Root cause: the vol-regime gate as an ENTRY precondition removes
trades that would have occurred in a low-vol regime but only reveals
themselves as low-vol AFTER the entry signal already required both a
9-day-MA dip and a Donchian breakout, so gating pre-entry vol regime
further compounds with the already-selective breakout signal and mostly
just reduces sample size / increases variance rather than removing bad
trades. This differs from the already-accepted BB-meanrev-QQQ construction
(2026-09-03-001) where the vol-regime gate WAS the primary discriminator
between working and non-working entries -- here the base signal's
selectivity (breakout + MA dip + uptrend) already does most of the
filtering, so an additional vol gate mostly just starves the strategy of
trades. Conclusion for future loops: this near-miss (2026-09-23-051) is
NOT rescuable via a simple vol-regime-gate bolt-on; a different fix
(e.g. wider Donchian window, different exit logic, or accepting it as a
scope-narrowed "low-vol-only, small-trade-count" strategy without gating)
would be needed if revisited again.
