# 2026-09-11 MFI Dual-Threshold Hold-Through-the-Middle State Machine (QQQ/SPY)

**Hypothesis:** Per QuantifiedStrategies.com's "How to Build a Profitable
Money Flow Index Strategy Using Python (Rules, Backtest)"
(https://www.quantifiedstrategies.com/how-to-build-a-profitable-money-flow-index-strategy-using-python/,
visited 2026-09-11), source's own disclosed rule: "whenever the indicator
is below threshold1, position=1; if the MFI is above threshold2,
position=-1; if neither condition is met, ... the position is held."
Long-only adaptation: long while MFI<entry_threshold OR mid-zone-and-was-
long; flat once MFI>exit_threshold, until MFI drops below entry_threshold
again. Distinct from all 6 prior repo MFI strategies (threshold-touch-
then-recover triggers, divergence, MA-cross, centerline-cross) -- this is
a wide dual-threshold state machine that holds through the entire middle
zone.

## Grid test (entry_threshold in [30,40,50] x exit_threshold in [65,75,85], QQQ/SPY/BTC-ETH, 3 vol terciles, 2018-01-01..2026-09-01)

- total_cells: 108, passed_cells: 18, **pass_fraction: 0.167**
- by_asset_class: equity 18/54 passed, crypto 0/54 passed (decisive rejection on crypto)
- by_vol_regime: low 12/36, mid 6/36, high 0/36 (edge concentrated in low/mid-vol regimes only)
- best_cell: entry_threshold=50, exit_threshold=85, SPY, low-vol, Sharpe=2.47

## Single-config validation (entry_threshold=50, exit_threshold=85 -- grid's best cell, full sample)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full sample) | 0.989 | 0.879 | >= 1.0 | **FAIL both (near-miss on QQQ)** |
| Max Drawdown | 0.355 | 0.341 | <= 0.25 | **FAIL both, decisively** |
| TC survival (10bps/trade, 8-10 trades/8yr) | 0.984 | 0.872 | >= 0.5 | PASS |
| Walk-forward (4 splits) | 1.0 | 1.0 | >= 0.75 | PASS |
| Parameter sensitivity (9-cell grid rel-std) | 0.295 | 0.153 | <= 0.5 | PASS |

## Decision: REJECTED

QQQ Sharpe is a near-miss (0.989 vs 1.0 threshold), but max drawdown fails
decisively on both symbols (0.355 QQQ / 0.341 SPY, both well above the
0.25 threshold) -- the wide entry_threshold=50/exit_threshold=85 config
that maximizes Sharpe in the grid also lets the state machine hold through
very large drawdowns (since it only exits once MFI clears an unusually
high 85 bar, which can take a long time in adverse conditions). Trade
count is thin (8-10 entries/8yr), consistent with holding one wide
position for extended periods rather than trading frequently. Edge is
also entirely absent in high-vol regime (0/36) and 0/54 on crypto. A
future iteration could try tightening exit_threshold or adding an explicit
MDD-based stop-loss on top of the state machine's own exit condition.
