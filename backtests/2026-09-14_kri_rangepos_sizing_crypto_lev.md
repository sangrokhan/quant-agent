# Backtest Report: KRI Range-Position Sizing Dial -- Crypto Leverage-Cap Follow-up

**Strategy file:** `strategies/2026-09-14_kri_rangepos_sizing_sma_trend.py` (same file, different params)
**Date:** 2026-09-14

## Hypothesis

Direct follow-up to 2026-09-14-180 (KRI range-position sizing dial,
accepted QQQ+SPY but crypto BTC/ETH decisively failed MDD at
leverage_cap=1.0). Per this cron trigger's repeatedly-confirmed
leverage-cap-recalibration fix pattern (TMF-124, Elder-Ray/Chaikin-Osc-125,
Ergodic-178, PVO-179): lowering leverage_cap for crypto (scaling
base_exposure/sensitivity proportionally down with it, and tightening
deadband back to 0.1 since MDD headroom is now much narrower) should let
the same underlying Sharpe edge clear the MDD cap.

## Config Scan

Scaled `base_exposure=0.4*leverage_cap, sensitivity=0.7*leverage_cap` at
leverage_cap in {0.3, 0.35, 0.4, 0.45} with deadband tightened to 0.1:
leverage_cap=0.3 was the only cap tested that kept BOTH BTC and ETH MDD
under 0.25 while Sharpe stayed above 1.0 for both (ETH is the tighter
constraint: MDD rises above 0.25 for lev>=0.35).

## Primary Config Validation (Step 7)

Config: `period=14, base_exposure=0.12, sensitivity=0.21, deadband=0.1,
leverage_cap=0.3`.

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| BTC/USDT | 1.515 (pass) | 0.151 (pass) | 0.747 (pass) | 1.00 (pass) | 0.039 rel-std (pass) |
| ETH/USDT | 1.078 (pass) | 0.216 (pass) | 0.589 (pass) | 1.00 (pass) | 0.059 rel-std (pass) |

All 5 validators pass for BOTH BTC/USDT and ETH/USDT.

## Decision

**ACCEPT for crypto (BTC/ETH) at leverage_cap=0.3.** Combined with
2026-09-14-180 (QQQ+SPY at leverage_cap=1.0), the KRI range-position
sizing dial is now accepted across all 4 symbols tested this trigger, at
asset-class-appropriate leverage caps and deadbands (equity 1.0x/db=0.5,
crypto 0.3x/db=0.1).
