# BVC Order-Flow Imbalance Momentum + Vol-Regime Gate — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_bvc_orderflow_volgate.py`
**Source:** Direct follow-up to this cron trigger's own near-miss
2026-09-09-024 (BVC order-flow imbalance momentum, ungated); reuses the
repo's established realized-vol-regime-gate construction from the accepted
`2026-09-03_bb_meanrev_qqq_volregime.py` / `2026-09-08-168`.

## Hypothesis

2026-09-09-024's grid breakdown showed the BVC imbalance edge concentrated
in the low-vol tercile (12/24 grid cells passed) vs mid (7/24) and high
(1/24). Hypothesis: adding an explicit realized-vol regime gate (trailing
20d realized vol <= vol_regime_ratio x trailing 1yr median), restricting
entries+exits to the low/mid-vol regime, should raise full-sample Sharpe
above the 1.0 threshold by excluding the decisively-underperforming
high-vol tercile.

## Grid test (Step 6)

`entry_threshold ∈ {0.10, 0.15, 0.20}` x `vol_regime_ratio ∈ {0.9, 1.0, 1.2}`
x {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles = 108 cells.

- **pass_fraction: 0.148** (16/108) — *worse* than the ungated predecessor's 0.278
- by_asset_class: equity 16/54, crypto 0/54 (decisive fail, as before)
- by_vol_regime: low 16/36, mid 0/36, high 0/36
- best_cell: QQQ, low-vol, `entry_threshold=0.15, vol_regime_ratio=1.2`, Sharpe 2.41

## Single-config validation (best config: `entry_threshold=0.15, vol_regime_ratio=1.2`)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.871 (FAIL, worse than ungated 0.953) | 0.707 (FAIL, worse than ungated 0.791) | ≥ 1.0 |
| Max drawdown | 0.171 (PASS) | 0.102 (PASS) | ≤ 0.25 |
| Net Sharpe after costs | 0.765 (PASS) | 0.538 (PASS, borderline) | ≥ 0.5 |

## Decision: REJECTED

The vol-regime-gate hypothesis is falsified: full-sample Sharpe on both QQQ
and SPY is *worse* than the ungated predecessor (2026-09-09-024), not
better, despite the gate correctly excluding the low-performing high-vol
tercile in isolation. The gate cuts trade count (QQQ 64→55, SPY 70→59) and
evidently removes some genuinely profitable mid/high-vol trades along with
the unprofitable ones — net effect is negative. This falsifies the
otherwise-productive "add a vol-regime gate to a near-miss" fix pattern
(which worked for KAMA/ATR-band 2026-09-06-183→accepted via Range Filter
[DW] 2026-09-08-168) for this particular BVC-imbalance construction: unlike
those prior successes, the ungated BVC signal's higher-vol-regime trades
were not simply noise, they contributed real edge that the gate discarded.
**Do not re-apply this same vol-gate construction to BVC imbalance in
future iterations without a different justification.**
