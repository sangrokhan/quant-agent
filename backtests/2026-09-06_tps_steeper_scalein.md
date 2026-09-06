# Backtest Report: TPS Steeper Scale-In (Rescue Attempt)

**Strategy file:** `strategies/2026-09-06_tps_steeper_scalein.py`
**Date:** 2026-09-06
**Hypothesis id:** 2026-09-06-186

## Hypothesis

Direct follow-up to near-miss 2026-09-06-185 (TPS Connors scale-in, QQQ
full-sample Sharpe 0.871, very low MDD 0.070, flagged as worth revisiting
via steeper scale-in weights). Tests changing the scale-in schedule from
10/20/30/40 (cumulative 10/30/60/100%) to a steeper 10/25/35/50 (reaching
full size roughly one day earlier on average), identical entry/exit logic
otherwise (200d EMA trend filter, 2-period RSI<25 entry, RSI>70 exit).

## Step 6 grid summary

Same param grid as predecessor: `rsi_entry_threshold in {20,25}` x
`rsi_exit_threshold in {65,70}`, same symbols/vol_regime_splits/date range.

- **pass_fraction: 0.146** (7/48) -- identical to predecessor
- **by_asset_class:** equity 7/24; crypto 0/24 (unchanged)
- **by_vol_regime:** low 3/16, mid 0/16, high 4/16 (unchanged)
- **best_cell:** same params as predecessor, QQQ/high-vol, Sharpe 1.72
  (vs predecessor's 1.70 -- essentially unchanged)

## Step 7 single-config validators (QQQ, `rsi_entry_threshold=25.0,
rsi_exit_threshold=70.0`, full sample)

| Validator | Passed | Value | Predecessor's value |
|---|---|---|---|
| sharpe_ratio | ❌ | **0.842** | 0.871 |
| max_drawdown | ✅ | 0.072 | 0.070 |
| transaction_cost_survival | ✅ | 0.623 | 0.639 |
| walk_forward | ✅ | 1.0 | 1.0 |
| parameter_sensitivity | ✅ | 0.089 | 0.086 |

## Decision: **REJECT (rescue hypothesis falsified)**

The steeper scale-in schedule did NOT improve the Sharpe -- it got
marginally *worse* (0.842 vs 0.871). Reaching full position size sooner
during a pullback does not capture meaningfully more upside in this
sample; if anything the earlier full commitment slightly increases exposure
to further adverse drawdown before the bounce, roughly offsetting any
upside gain. All other metrics (MDD, parameter sensitivity, walk-forward)
are essentially unchanged from the predecessor, confirming the core
edge/limitation is dominated by the entry/exit trigger logic (200d EMA +
2-period RSI thresholds), not the specific scale-in weight schedule. Not
flagged for further scale-in-weight tuning; the original near-miss
(2026-09-06-185) remains open to other rescue mechanisms (e.g. trend-
strength filter, different RSI window) in a future iteration.
