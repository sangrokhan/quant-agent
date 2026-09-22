# Reverse Elder Impulse — Min-Hold-Days Rescue (2026-09-22)

## Rescue context

Direct rescue attempt for this same cron trigger's own rejection
2026-09-22-071 (Reverse Elder Impulse Neutral->Negative transition trigger,
decisive Sharpe+TC-survival near-miss fail both QQQ/SPY; MDD/walk-forward/
param-sensitivity already passed at the base config). Adds a
`min_hold_days` gate (ignore the Neutral-state exit trigger until N days
elapsed once in a position) — repo precedent:
`strategies/2026-09-04_kvo_crossover_minhold.py`.

## Grid summary (min_hold_days in {5, 10, 15})

- `pass_fraction` = 0.167 (6/36)
- `by_asset_class`: equity 6/18, crypto 0/18
- `by_vol_regime`: low 6/12, mid 0/12, high 0/12
- Best full-sample-average equity config: QQQ min_hold_days=15 (avg Sharpe 1.32); SPY min_hold_days=5 (avg Sharpe 1.41), SPY min_hold_days=15 close behind (1.295)
- Primary config validated: `min_hold_days=15` (best QQQ average, still solid on SPY)

## Single-config validation (min_hold_days=15)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio | 1.052 **PASS** | 0.879 **FAIL** |
| Max drawdown | 0.284 **FAIL** (>0.25, up from base 0.191) | 0.289 **FAIL** (>0.25, up from base 0.187) |
| TC-survival (10bps/trade) | 0.914 **PASS** (up from base 0.443 -- 151 trades vs 289) | 0.711 **PASS** (up from base 0.498 -- 153 trades vs 293) |
| Walk-forward (4 splits) | 1.0 **PASS** | 1.0 **PASS** |
| Parameter sensitivity | 0.817 **FAIL** (>0.5, up from base 0.486) | 0.416 **PASS** |

## Decision: REJECT

The min-hold rescue worked exactly as intended on the dimension it targeted
— TC-survival now clears the bar comfortably on both symbols (roughly
halving trade count from ~290 to ~152). But holding a position for a
mandatory 15 trading days increases exposure to adverse moves inside that
window, pushing max drawdown above the 0.25 threshold on both symbols (it
had passed at the base config) and QQQ's Sharpe-across-parameter-values
became unstable (param-sensitivity fails: relative_std 0.82). SPY's Sharpe
also slipped below 1.0. Net result: fixed one failure mode (costs) by
introducing two new ones (drawdown, and on QQQ, parameter instability) — a
worse trade-off than the base rejection. No config in this grid clears all
5 validators.

Source: https://www.tradinformed.com/how-to-trade-the-sp500-using-the-impulse-indicator/ (same as 2026-09-22-071)
