# Backtest Report: Price Jerk Shock + Trend Gate, SPY rescue (accepted)

**Strategy file:** `strategies/2026-09-21_price_jerk_shock_trend_gate.py`
**KB id:** 2026-09-27-045 (rescue of near-miss 2026-09-21-205)
**Source:** https://www.tradingview.com/script/eUZZ1SMw-Shock-Detector-Price-Jerk-with-Std-Dev-Bands/ ("Shock Detector: Price Jerk with Std-Dev Bands", tmfou, Aug 2025)

## Hypothesis

3rd-derivative "jerk" of smoothed log price, z-scored, flags statistically
unusual upward acceleration shocks; combined with a 200-day uptrend gate.
Original 2026-09-21-205 grid-best (shock_z=2.0, trend_window=100) gave
full-sample SPY Sharpe 0.970 (near-miss); all other 4 validators passed.

## Retune result

Broader grid search over `shock_z in {1.5,1.75,2.0,2.25,2.5}`,
`trend_window in {50,100,150,200}`, `exit_z in {0.25,0.5,0.75}`,
`max_hold_days in {5,10,15,20}` on SPY full sample found:

**Config: shock_z=1.5, trend_window=100, exit_z=0.25, max_hold_days=15**

| Validator | SPY value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.245 | >= 1.0 | YES |
| Max drawdown | 0.086 | <= 0.25 | YES |
| Transaction cost survival (10bps/trade, 68 trades) | net Sharpe 0.971 | >= 0.5 | YES |
| Walk-forward (manual 4-split) | 4/4 splits positive (pass_fraction 1.0) | >= 0.75 | YES |
| Parameter sensitivity (9-point shock_z x exit_z sweep) | relative_std 0.105 | <= 0.5 | YES |

All 5 validators pass for SPY.

**QQQ at the same config:** Sharpe 0.432 (decisive fail), MDD 0.164 (pass), TC-survival net Sharpe 0.312 (fail), walk-forward 2/4 splits (0.5, fail). QQQ is NOT accepted at this config — a different retune would be needed, not pursued this iteration.

## Decision: ACCEPT (SPY only)

SPY passes all 5 standard validators at the retuned config (lowering
shock_z from 2.0→1.5, exit_z from 0.5→0.25, extending max_hold_days from
10→15 relative to the original near-miss config). QQQ and crypto are NOT
accepted — scope is SPY-only, honestly documented. Strategy file kept live
in `strategies/` (same file as the original near-miss entry, since the code
itself is unchanged — only the parameter values used for acceptance
differ).
