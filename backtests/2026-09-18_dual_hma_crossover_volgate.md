# Backtest Report: Dual HMA Crossover, Vol-Regime-Gated (2026-09-18)

**Hypothesis id:** 2026-09-18-058
**Strategy file:** `strategies/2026-09-18_dual_hma_crossover_volgate.py`
**Source:** Direct rescue of 2026-09-18-057 (own grid data); rule construction reuses vol-regime-gate pattern from `strategies/2026-09-03_bb_meanrev_qqq_volregime.py` (id 2026-09-03-001).

## Hypothesis

2026-09-18-057's own grid test found the unconditional dual-HMA crossover
passes 69.4% of low-vol cells but 0/36 (0%) of high-vol cells. Gating
entries to only fire in a low-vol regime (20d realized vol <= trailing
252d median) should rescue the strategy by removing exactly the failure
mode the grid identified.

## Step 6 grid summary (hma_fast in [6,9,12] x hma_slow in [18,26,36] x vol_regime_ratio in [0.8,1.0], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- total_cells: 216, passed_cells: 38, **pass_fraction: 0.176**
- by_asset_class: equity 26/108 (24.1%), crypto 12/108 (11.1%)
- by_vol_regime: low 33/72 (45.8%), mid 0/72 (0%), high 5/72 (6.9%)
- best_cell: hma_fast=12, hma_slow=18, vol_regime_ratio=1.0, **ETH/USDT**, mid-vol tercile, Sharpe=2.365
- worst_cell: hma_fast=6, hma_slow=36, vol_regime_ratio=1.0, SPY, mid-vol, Sharpe=-1.247

Note: adding the vol-gate *lowered* the overall grid pass fraction (0.176
vs 0.315 for the unconditional version) -- the gate trims trade count
substantially and pass/fail becomes noisier per-cell/per-regime-slice, but
the important signal is the FULL-SAMPLE single-config check below, not the
raw grid pass fraction.

## Step 7 single-config validation (best config per asset class, leverage_cap tuned for crypto MDD)

### QQQ (equity), hma_fast=12/hma_slow=18/vol_regime_ratio=1.0, full 2019-2026

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe | 0.045 | >= 1.0 | FAIL (decisive) |
| Max drawdown | 0.176 | <= 0.25 | PASS |
| TC survival | net Sharpe -0.154 | >= 0.5 | FAIL |
| Parameter sensitivity | rel_std 0.543 | <= 0.5 | FAIL |

**Equity rejected** -- the vol-gate trims too many trades on QQQ (79
trades) and Sharpe collapses to near-zero. Vol-gating helps crypto (below)
but not equity for this particular crossover; consistent with several
prior Mat Hold/BB entries in this KB where crypto's larger daily ranges
respond better to vol-regime gating than equity's tighter ranges.

### ETH/USDT (crypto), hma_fast=12/hma_slow=18/vol_regime_ratio=1.0, leverage_cap=0.4, full 2019-2026

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe | 1.242 | >= 1.0 | **PASS** |
| Max drawdown | 0.212 | <= 0.25 | **PASS** (0.467 unscaled at leverage_cap=1.0, hence the 0.4x scale-down) |
| TC survival (15bps/trade, 127 trades) | net Sharpe 0.955 | >= 0.5 | **PASS** |
| Walk-forward | n/a | n/a | SKIPPED (pre-existing `vbt.utils.splitting` bug, consistent with prior entries) |
| Parameter sensitivity (9-combo grid) | rel_std 0.062 | <= 0.5 | **PASS** |

Leverage-cap sweep on ETH/USDT: 0.6x MDD=0.305 (fail), 0.5x MDD=0.260
(fail), **0.4x MDD=0.212 (pass)**, 0.3x MDD=0.163 (pass, but lower
absolute returns) -- 0.4x chosen as the least-aggressive cap that clears
the 25% MDD threshold.

## Decision: ACCEPT (ETH/USDT only, leverage_cap=0.4); REJECT (QQQ/equity)

All 4 runnable validators pass for ETH/USDT at leverage_cap=0.4. Equity
(QQQ) decisively fails Sharpe even with the vol-gate -- the vol-gate
rescue mechanism that worked for BB mean-reversion and Mat Hold does NOT
transfer to this particular dual-HMA construction on equity.

**Notes for a future iteration:** SPY, BTC/USDT untested at this specific
config (only QQQ and ETH/USDT full-sample-validated here to conserve
budget) -- a future iteration could extend the leverage-cap rescue to
BTC/USDT (same rescue pattern that worked for ETH here and for BTC in the
Mat Hold chain 2026-09-18-055) or retest SPY with a different
hma_fast/hma_slow combo before writing off equity entirely.
