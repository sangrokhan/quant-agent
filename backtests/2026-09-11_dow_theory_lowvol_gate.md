# Backtest Report: Dow Theory Confirmation + Low-Vol Regime Gate

**Strategy file:** `strategies/2026-09-11_dow_theory_lowvol_gate.py`
**Date:** 2026-09-11
**Direct fix attempt for:** 2026-09-11-051 (rejected: decisive full-sample
Sharpe/MDD failure despite the grid showing the edge concentrated entirely
in low-vol regimes -- 100% pass in low-vol tercile vs 0% in high-vol tercile)

## Hypothesis

Same Dow Theory (Industrials/Transports new-high confirmation, IYT as
confirm leg for equity, ETH as confirm leg for crypto) core as
2026-09-11-051, plus a new-entry-only causal realized-vol percentile gate
(only take a fresh long entry when trailing 20-day realized vol is at/below
its own trailing-252-day percentile rank threshold), following this repo's
established fix pattern (2026-09-03-021) for trend/breakout strategies that
only work in low-vol regimes.

## Grid test summary (Step 6)

Grid: `vol_percentile_threshold` in {0.4, 0.5, 0.6} (lookback_window=50,
confirm_lag_days=3 fixed from 051's best config), vol_regime_splits=3,
symbols equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT}.

- **Equity:** 6/18 cells passed (0.333 pass_fraction). By vol regime: low
  6/6 (100%), mid 0/6 (0%), high 0/6 (0%). Best cell: SPY, low-vol,
  vol_percentile_threshold=0.6, Sharpe 2.47. Worst: SPY, mid-vol, Sharpe
  -0.63.
- **Crypto:** 0/18 cells passed (0.0 pass_fraction), confirming
  falsification again.

The gate did NOT broaden the edge beyond low-vol -- the pattern is
identical to the ungated 051 strategy (low-vol only, mid/high-vol still
fail). This suggests the underlying dual-new-high-confirmation signal
itself only works structurally in calm markets, and a vol-regime gate on
entries alone can't fix that (positions opened just before a vol regime
shift still get carried into it, since the gate only blocks new entries,
not existing ones).

## Single-config validation (Step 7): vol_percentile_threshold=0.6

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.582 ❌ | 0.492 ❌ | ≥ 1.0 |
| Max drawdown | 0.304 ❌ | 0.248 ✅ (marginal) | ≤ 0.25 |
| Transaction-cost survival (10bps/trade) | 0.560 ✅ | 0.458 ❌ | ≥ 0.5 |
| Walk-forward (manual 4-split) | 1.00 (4/4) ✅ | 1.00 (4/4) ✅ | ≥ 0.75 |
| Parameter sensitivity (relative std) | 0.084 ✅ | 0.050 ✅ | ≤ 0.5 |

MDD improved slightly for SPY (0.336 -> 0.248, now marginally passing) but
QQQ's MDD still fails (0.304 vs 0.25) and Sharpe fails decisively for both
symbols; SPY's TC-survival newly fails as trade count/timing shifted.
Overall the fix did not clear the bar.

## Decision: REJECTED

The low-vol regime gate is a genuine partial improvement (SPY MDD now
passes) but does not fix the core issue: Sharpe still fails decisively on
both symbols, and QQQ's MDD and SPY's TC-survival still fail. Confirms
2026-09-11-051's own diagnosis that the underlying Dow Theory dual-new-high
confirmation edge is real but too narrow (only manifests cleanly in
low-vol regimes and the entry-only gate can't fully contain drawdowns from
carried positions into worse regimes). Not recommending further iteration
on this specific mechanism without a more aggressive exit-side vol gate
(e.g. force-flatten on a vol-regime flip mid-position, not just block new
entries) -- flagging as a possible future direct-fix-of-a-fix candidate.
