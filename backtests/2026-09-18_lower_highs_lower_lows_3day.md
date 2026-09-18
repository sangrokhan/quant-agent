# Backtest Report: Lower Highs & Lower Lows 3-Day Reversal (QQQ, max_hold_days=10)

**Date:** 2026-09-18
**Status:** REJECTED (near-miss)

## Hypothesis

Source: https://www.quantifiedstrategies.com/lower-highs-and-lower-lows-pattern/

Three consecutive daily bars each making a lower high AND a lower low than
the prior bar signal a short-term reversal; source's disclosed rule: "go
long at the close of the third consecutive lower low and lower high [day],
sell after n bars," reported as outperforming the 1-day and 2-day variants
on SPY/GLD/TLT (exact tables paywalled but mechanical entry/exit
disclosed). Adapted long-only, `max_hold_days` and `consecutive_days`
tunable.

## Step 6 grid summary (`grid_result_lower_highs_lower_lows_3day.json`)

- param_grid: `max_hold_days` in [1, 5, 10] (consecutive_days fixed at 3, per source's best-performing variant)
- symbols: equity (QQQ, SPY), crypto (BTC/USDT, ETH/USDT)
- vol_regime_splits: 3
- **pass_fraction: 0.139 (5/36 cells)**
- by_asset_class: equity 5/18, crypto 0/18 (decisive crypto reject)
- by_vol_regime: low 5/12, mid 0/12, high 0/12
- best_cell: QQQ, max_hold_days=10, low-vol regime, Sharpe 1.80
- worst_cell: BTC/USDT, max_hold_days=10, mid-vol regime, Sharpe -0.84

## Step 7 single-config validation (QQQ, max_hold_days=10, full sample 2015-01-01 to 2026-09-01)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.663 | >= 1.0 |
| Max drawdown | pass | 0.174 | <= 0.25 |
| TC survival (10bps/trade, 81 trades) | pass | net Sharpe 0.585 | >= 0.5 |
| Walk-forward (4 splits) | pass | 1.0 pass fraction | >= 0.75 |
| Parameter sensitivity (max_hold_days 1/5/10) | **FAIL** | rel_std 0.532 | <= 0.5 |

## Decision: REJECT (near-miss)

3 of 5 validators pass (MDD, TC survival, walk-forward all comfortably
pass), but full-sample Sharpe (0.66) misses the 1.0 threshold and
parameter sensitivity (0.532) marginally exceeds 0.5. Similar profile to
the 123-pattern near-misses: isolated low-vol tercile performance (Sharpe
1.80 on QQQ) is materially stronger than full-sample, suggesting this
could be a regime-gating rescue candidate in a future iteration (same
pattern as 2026-09-18-091's attempt). Crypto is decisively rejected across
the whole grid (0/18).

Left `strategies/2026-09-18_lower_highs_lower_lows_3day.py` in place as a
near-miss record for a future low-vol-regime-gated rescue attempt.
