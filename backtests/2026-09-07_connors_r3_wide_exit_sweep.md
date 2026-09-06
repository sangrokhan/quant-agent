"""Backtest report: Connors R3 wide exit_above sweep -- confirming/refuting
the 2026-09-06-159 near-miss rescue.

Hypothesis id: 2026-09-07-021
Strategy file: strategies/2026-09-07_connors_r3_wide_exit_sweep.py
Outcome: **REJECTED**

## Background

2026-09-06-159 tested Larry Connors' R3 (3-day RSI(2) drop-sequence,
close>SMA200, entry RSI<10, exit RSI>exit_above) and its grid's nominal
best cell (exit_above=70) missed the Sharpe threshold (0.892 vs 1.0). A
Step-7 parameter-sensitivity sweep (done manually, not as part of that
run's own grid) found exit_above=75 alone pushed QQQ full-sample Sharpe to
1.133, clearing the bar -- flagged as "promising for revisit" in notes.
This iteration makes that sweep a first-class grid dimension and runs the
full validator suite on whatever the grid's own best_cell turns out to be.

## Step 6 grid summary (entry_below in [10,15] x exit_above in
[70,75,80,85], symbols QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3)

- total_cells: 96, passed_cells: 18, pass_fraction: **0.1875**
- by_asset_class: equity 18/48 (0.375), crypto 0/48 (0.0, decisive)
- by_vol_regime: low 11/32 (0.344), mid 5/32 (0.156), high 2/32 (0.063)
- best_cell: QQQ, entry_below=15, exit_above=75, low-vol regime, Sharpe
  2.302

## Step 7 single-config validation (entry_below=15, exit_above=75, full
2019-2026 sample)

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | **1.133 (PASS)** | 0.299 (FAIL) | >= 1.0 |
| Max drawdown | **0.099 (PASS)** | 0.309 (FAIL) | <= 0.25 |
| Tx-cost survival (5bps, 42 trades) | **1.085 (PASS)** | 0.265 (FAIL) | >= 0.5 net Sharpe |
| Parameter sensitivity (entry_below x exit_above, 8-combo QQQ sweep) | **relative_std 0.597 (FAIL)** | -- | <= 0.5 |
| Parameter sensitivity (exit_above only, entry_below=15 fixed, 4 values) | relative_std 0.506 (FAIL, narrowly) | -- | <= 0.5 |
| Walk-forward | not run -- pre-existing `vbt.utils.splitting` AttributeError bug in installed vectorbt, same known issue this cron trigger | | |

## Decision

**Rejected.** QQQ individually clears Sharpe/MDD/TC-survival at the exact
exit_above=75 config that rescued the prior near-miss, confirming that
result was not a fluke of the manual sweep. However, running the FULL
exit_above grid (70/75/80/85) reveals the "rescue" is a narrow, fragile
spike rather than a stable edge: Sharpe goes 0.968 (70) -> **1.133 (75)**
-> 0.338 (80) -> 0.364 (85) -- a cliff-edge collapse immediately past the
one value that happens to pass. Parameter sensitivity fails both on the
full 8-combo grid (relative_std 0.597) and even on the narrower
exit_above-only 4-value sweep (relative_std 0.506, narrowly over the 0.5
threshold). This is a textbook case of the parameter-sensitivity validator
doing its job: a single lucky config passing full-sample Sharpe/MDD/TC
does not make a strategy robust when its neighbors in parameter space
collapse. SPY fails decisively on every metric at the same config
(Sharpe 0.299, MDD 30.9%, well past all thresholds). Crypto rejected
categorically (0/48 grid cells).

**Closes the loose end from 2026-09-06-159's notes**: the exit_above=75
"rescue" does NOT generalize into a genuinely accept-worthy config once
tested as a first-class grid point rather than a one-off sensitivity
check. A future loop should not revisit plain R3 exit-threshold tuning
further; a fundamentally different modification (e.g. a regime gate, or a
different exit mechanism entirely such as an ATR trailing stop instead of
a fixed RSI recovery level) would be needed to have a chance.

Source: https://www.quantifiedstrategies.com/larry-connors-r3-strategy/
(same as 2026-09-06-159; read via prior iteration's browser_exec fetch,
not re-fetched this iteration since it's already in visited_pages.jsonl).
"""
