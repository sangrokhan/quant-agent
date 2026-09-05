# 2026-09-05 — DPO + Directional Movement + Parabolic SAR Triple Confirmation (SPY accepted)

## Hypothesis
Per FBS.eu's "ADX and DPO strategy" (Google search snippet; source page
404'd): long entry requires THREE simultaneous confirmations on the same
bar: (1) DPO crosses above its zero line, (2) +DM crosses above -DM
(directional trend confirmation), (3) Parabolic SAR is in its bullish state
(below price). Exit when SAR flips bearish (above price) or a
`max_hold_days` time-stop. Distinct from plain DPO zero-cross
(2026-09-04-056, accepted, DPO alone) and plain Parabolic SAR + SMA trend
filter (2026-09-04-042, accepted QQQ only) -- no prior strategy in this repo
requires all three signals together.

## Grid test (validation/grid_test.py, run_strategy_grid)
- `param_grid`: dpo_window in [15,20,30], di_window in [10,14]
  (max_hold_days fixed at 20)
- symbols: equity [QQQ, SPY], crypto [BTC/USDT, ETH/USDT]
- vol_regime_splits=3
- 72 total cells, **19 passed (pass_fraction = 0.264)**
- by_asset_class: equity 19/36 passed; **crypto 0/36 passed** (decisive reject)
- by_vol_regime: low 11/24, mid 5/24, high 3/24
- best full-config: SPY, dpo_window=20, di_window=10 -- **passed all 3/3
  vol regimes** (only config to do so)
- best_cell: QQQ dpo_window=20/di_window=10, low-vol, Sharpe=2.08 (but QQQ
  full-sample fails, see below)

## Single-config validation (dpo_window=20, di_window=10, max_hold_days=20)

| Metric | SPY | QQQ | Threshold |
|---|---|---|---|
| Sharpe (full period) | **1.311 (PASS)** | 0.712 (FAIL) | >= 1.0 |
| Max drawdown | 0.106 (PASS) | 0.222 (PASS) | <= 0.25 |
| Net Sharpe after costs (10bps/trade) | **1.227 (PASS)** | 0.653 (PASS) | >= 0.5 |
| Walk-forward (manual 4-split) | 1.0 (PASS) | 1.0 (PASS) | >= 0.75 |
| Parameter sensitivity (dpo_window in [15,20,30], SPY) | relative_std=0.132 (PASS, threshold 0.5) | -- | -- |

Walk-forward note: manual 4-contiguous-chunk date split used (vbt
`utils.splitting` AttributeError bug workaround, consistent with other
recent entries).

## Decision: ACCEPTED for SPY only
SPY passes every validator run: Sharpe 1.31, MDD 10.6%, net Sharpe after
costs 1.23 (25 trades, no over-trading concern), walk-forward 4/4 splits
positive, and parameter sensitivity to `dpo_window` is low
(relative_std=0.13, well under the 0.5 threshold). QQQ fails the Sharpe
threshold (0.712) despite similar signal frequency (29 trades) and passing
MDD/TC-survival/walk-forward -- kept as rejected/near-miss, not deployed.
Crypto rejected decisively (0/36 grid cells across BTC/USDT, ETH/USDT).

## Notes for future iterations
This triple-confirmation construction (cyclical + directional + trailing-
stop-reversal all agreeing) produced the strongest and most parameter-
robust SPY result in recent iterations, and is the first Parabolic-SAR-based
strategy in this repo to pass validators without needing a separate slow-SMA
trend filter (the DPO+DM gates apparently substitute for that role). Scope
is equity-only (SPY); do not extrapolate to QQQ or crypto.
