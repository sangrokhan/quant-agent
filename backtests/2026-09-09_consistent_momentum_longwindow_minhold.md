# Backtest report: Consistent Momentum (long window + min_hold turnover fix)

**Strategy file:** `strategies/2026-09-09_consistent_momentum_longwindow_minhold.py`
**Knowledge base id:** 2026-09-09-108
**Outcome:** REJECTED (direct follow-up fix for rejected 2026-09-09-107)

## Hypothesis

Direct fix attempt per 2026-09-09-107's own rejection notes: widen the
consistency-window toward Quantpedia's true ~126-day (6-month) formation
period, and add a `min_hold_days` gate suppressing exit signals for the
first N bars after entry (same fix pattern proven for Klinger 2026-09-04-085
/ ZLEMA 2026-09-06-171 / Accelerator Oscillator 2026-09-06-174).

## Grid test summary (Step 6)

- Grid: `lookback_days` in [63, 126] x `min_hold_days` in [10, 20, 30] x
  {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles = 72 cells.
- `pass_fraction`: **0.208** (15/72) -- essentially unchanged from parent's 0.229
- `by_asset_class`: equity 15/36, crypto 0/36
- `by_vol_regime`: low 12/24, mid 3/24, high 0/24
- Best cell: SPY, low-vol tercile, `lookback_days=126, min_hold_days=20`,
  Sharpe 2.625

## Single-config validation (Step 7), best grid config

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| SPY | 0.777 (fail) | 0.199 (pass) | 0.725 (**pass**) | 0.5 (fail) | 0.285 (pass) |
| QQQ | 0.677 (fail) | 0.331 (fail) | 0.652 (**pass**) | 0.75 (pass) | 0.094 (pass) |

## Verdict

The turnover fix worked exactly as diagnosed: TC-survival now passes both
symbols (trades cut from 193/178 to 35/27, net Sharpe recovered to
0.725/0.652). But full-sample Sharpe still falls short of 1.0 on both
symbols, SPY now fails walk-forward, and QQQ still fails MDD. Removing the
mechanical turnover drag wasn't enough -- the underlying two-window
consistency signal itself tops out around Sharpe 0.6-0.8. Not accepted.
This closes out the Consistent Momentum idea for this repo after two
attempts.
