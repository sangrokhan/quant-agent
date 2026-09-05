# VIX/VIX3M Term-Structure Backwardation Regime Filter — Backtest Report

**Hypothesis:** VIX/VIX3M ratio >= 1.0 signals term-structure backwardation
(acute stress); ratio falling back below threshold after backwardation is a
buy signal (fear subsiding). Flat during backwardation, long otherwise, with
a short recovery/min-hold window after the flip to reduce whipsaw.

**Source:** https://volatilitybox.com/research/vix-contango-backwardation/
(gives the VIX/VIX3M >= 1.0 threshold convention and the "end of
backwardation = buy signal" framing).

**Strategy file:** `strategies/2026-09-05_vix_vix3m_backwardation_regime.py`

## Step 6 — Grid test summary (param_grid: backwardation_threshold in
[0.95, 1.0, 1.05] x recovery_lookback in [5, 10, 20]; symbols: equity
QQQ/SPY, crypto BTC/USDT, ETH/USDT; vol_regime_splits=3; period
2019-01-01..2026-09-01)

- total_cells: 108, passed_cells: 27, **pass_fraction: 0.25**
- by_asset_class: equity 27/54 (50%), crypto 0/54 (0%)
- by_vol_regime: low 18/36, mid 6/36, high 3/36
- best_cell: backwardation_threshold=1.05, recovery_lookback=5, QQQ, low-vol
  regime, Sharpe=2.58
- worst_cell: backwardation_threshold=0.95, recovery_lookback=5, QQQ,
  high-vol regime, Sharpe=-0.51

Crypto: complete failure (0/54) — the SPX-options-derived VIX/VIX3M regime
signal does not transfer to crypto's own volatility regimes at all; expected
given VIX is an equity-index-options construct.

## Step 7 — Single-config validators (best grid config: threshold=1.05,
recovery_lookback=5, min_hold_days=3)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | **PASS** 1.106 | **PASS** 1.114 |
| Max Drawdown (<= 0.25) | **FAIL** 0.356 | **FAIL** 0.254 (near-miss) |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade, 24 trades) | **PASS** 1.086 | not re-run (QQQ representative) |
| Parameter sensitivity (relative_std <= 0.5, 9-cell QQQ sweep) | **PASS** 0.155 | n/a |

Walk-forward not run: `check_walk_forward` hits the pre-existing
`vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt
version (consistent with other recent entries in this log).

Default/less-tuned config (threshold=1.0, recovery_lookback=10) was worse:
QQQ Sharpe 0.90 (fail), MDD 0.458 (fail) — the strategy only clears Sharpe
at the more aggressive 1.05 threshold / short 5-day recovery window, and
even then MDD fails on QQQ and is a near-miss fail on SPY.

## Outcome: **REJECTED**

Max drawdown fails decisively on QQQ (0.356 vs 0.25) and narrowly on SPY
(0.254 vs 0.25) even at the best-performing grid config; Sharpe alone passes
but MDD is the binding constraint. Crypto asset class fails completely
(0/54 cells) — the equity-options-derived regime signal has no edge there.
Equity/low-vol regime is a genuine near-miss (Sharpe > 1, MDD only slightly
over threshold on SPY) worth revisiting with either a stricter recovery/
min-hold gate to reduce drawdown-producing whipsaws, or combined with an
independent trend filter to reduce time-in-market during high-vol stretches
that still fail the flat criterion.
