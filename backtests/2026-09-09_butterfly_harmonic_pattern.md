# Butterfly Harmonic Pattern (Bullish) — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_butterfly_harmonic_pattern.py`
**Hypothesis source:** https://dhan.co/blog/technical-analysis/harmonic-butterfly-pattern/

## Hypothesis

The Harmonic Butterfly pattern is a 5-point XABCD Fibonacci reversal pattern
distinct from the already-tested Gartley (2026-09-08-108, rejected) and Bat
(2026-09-09-017, rejected) patterns: B retraces ~78.6%-88.6% of XA (much
deeper than Bat's 38.2-50%), C retraces 38.2%-88.6% of AB, and D — the
Potential Reversal Zone — OVERSHOOTS point X by ~27.2% of the XA leg
(D lies beyond the pattern's starting point, unlike Gartley/Bat/AB=CD which
complete D inside the XA range). Entry at the D touch, stop just beyond D,
target a partial retracement of CD back toward C.

## Grid test (Step 6)

`param_grid={"pivot_window": [7,11,15], "max_hold_days": [10,20]}`,
symbols QQQ/SPY/BTC-USDT/ETH-USDT, `vol_regime_splits=3`, 2019-01-01 to
2026-09-01.

- **72 total cells, 8 passed (pass_fraction 0.111)**
- By asset class: equity 8/36, **crypto 0/36 (decisive fail)**
- By vol regime: low 0/24, mid 0/24, **high 8/24** — edge entirely
  concentrated in the high-vol tercile, zero passes elsewhere
- Best cell: SPY, pivot_window=11/max_hold_days=10, high-vol regime, Sharpe 1.30

## Single-config validators (pivot_window=11, max_hold_days=10)

| Symbol | Trades | Sharpe (full) | MDD | TC-survival (net Sharpe) | Walk-forward (manual 4-split) | Param sensitivity (relative std) |
|---|---|---|---|---|---|---|
| QQQ | 2 | 0.025 **FAIL** (thr 1.0) | 0.103 PASS | 0.014 **FAIL** (thr 0.5) | 0.75 pass_fraction PASS | 3.29 **FAIL** (thr 0.5) |
| SPY | 3 | 0.670 **FAIL** (thr 1.0) | 0.016 PASS | 0.642 PASS | 1.00 pass_fraction PASS | 0.39 PASS |

Walk-forward used the repo's standard manual 4-equal-slice fallback
(`vbt.utils.splitting.RangeSplitter` is unavailable in this environment's
vectorbt build — same known issue documented in prior backtest reports).

## Decision: REJECTED

Both QQQ and SPY fail the full-sample Sharpe >= 1.0 bar decisively (0.025
and 0.670). Signal is extremely sparse (2-3 trades over 7.5 years on
daily bars) — the pattern's strict 3-simultaneous-Fibonacci-ratio
requirement (AB~0.786-0.886, BC 0.382-0.886, D overshoot ~0.272 beyond X)
rarely fires. The grid's apparent 8/72 pass fraction concentrated
exclusively in the high-vol tercile is a small-sample artifact (best cell
Sharpe 1.30 on a handful of high-vol-regime trades) that does not survive
full-sample testing, the same pattern seen repeatedly with other rare-signal
harmonic/pattern strategies in this repo (Gartley 0/48, Bat 0/72). Crypto
failed all 36 grid cells decisively. QQQ additionally fails
parameter-sensitivity badly (relative_std 3.29) — Sharpe swings from -0.28
to +∞ (single-trade artifacts) across the pivot_window sweep, confirming the
signal is too sparse for a stable parameter estimate.

No further Butterfly-harmonic variant recommended without a fundamentally
looser Fibonacci-tolerance construction (e.g. wider `d_tolerance`,
`bc_min`/`bc_max` bands) to generate enough trades for a meaningful test —
but doing so would drift from the pattern's own defining ratios. This closes
out the harmonic-pattern family (Gartley, Bat, Butterfly, AB=CD, Crab all
now tested) for daily-bar QQQ/SPY/BTC/ETH.
