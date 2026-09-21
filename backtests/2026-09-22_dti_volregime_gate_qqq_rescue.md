# Backtest Report: DTI + Vol-Regime Gate (QQQ rescue attempt)

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_dti_volregime_gate_qqq_rescue.py`

## Hypothesis

Direct fix attempt for this cron trigger's own prior near-miss rejection
(2026-09-22-023, ungated DTI zero-line crossover): add an explicit
realized-vol regime gate (flatten when trailing 20d vol > vol_regime_ratio
* trailing 252d median) on top of the identical DTI entry/exit logic, since
that entry's own grid showed the high-vol tercile decisively fails (0/36)
across all symbols/configs.

## Step 6 — Grid test summary

Grid: `max_hold_days` in {15, 20, 30}, `vol_regime_ratio` in {0.8, 1.0, 1.2},
symbols {QQQ, SPY, BTC/USDT, ETH/USDT}, vol_regime_splits=3 (108 cells).

- **pass_fraction: 0.204** (22/108) -- LOWER than ungated version's 0.278
- **by_asset_class:** equity 20/54; crypto 2/54
- **by_vol_regime:** low 20/36; mid 2/36; high 0/36
- **best_cell:** SPY low-vol, `max_hold_days=20, vol_regime_ratio=1.2`, Sharpe 2.56

## Step 7 — Single-config validators (grid-best config: max_hold_days=20, vol_regime_ratio=1.2)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | FAIL 0.828 (was 0.962 ungated) | **FAIL 0.974** (was 1.117 ungated, PASSING) |
| Max Drawdown (<=0.25) | **PASS 0.195** (was 0.282 ungated, FAILING) | PASS 0.112 |
| TC-survival | PASS 0.702 | PASS 0.790 |
| Walk-forward | skipped (same pre-existing tooling bug) |
| Parameter sensitivity | PASS 0.134 | PASS 0.288 |

## Step 8 — Decision: REJECT (rescue hypothesis falsified)

The vol-regime gate DID fix QQQ's MDD (0.282 -> 0.195, now passing) but
made Sharpe WORSE on both symbols (QQQ 0.962->0.828; SPY 1.117->0.974,
flipping SPY from a clean accept to a near-miss reject). This is the same
failure mode recorded elsewhere in this knowledge base (e.g. 2026-09-09-089)
for vol-gating a trend-following crossover signal: the gate removes some of
the fast whipsaw-adjacent trades that actually anchor the signal's edge,
net negative overall despite improving the worst-case drawdown.

**Conclusion:** keep the original ungated DTI strategy's SPY-only accept
(2026-09-22-023) as the live strategy; this vol-gated variant is rejected
and not deployed.
