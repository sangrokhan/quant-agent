# Backtest Report: Ergodic Oscillator Sizing Dial -- Crypto Leverage-Cap Follow-up

**Strategy file:** `strategies/2026-09-14_ergodic_sizing_sma_trend.py` (same file, different params)
**Date:** 2026-09-14

## Hypothesis

Direct follow-up to 2026-09-14-176 (Ergodic Oscillator continuous sizing
dial, accepted QQQ+SPY but crypto BTC/ETH decisively failed MDD at
leverage_cap=1.0, base_exposure=0.8, sensitivity=0.9). Per this cron
trigger's now-repeatedly-confirmed leverage-cap-recalibration fix pattern
(TMF 2026-09-14-124, Elder-Ray/Chaikin-Osc 2026-09-14-125): lowering
leverage_cap for crypto (scaling base_exposure/sensitivity proportionally
down with it) should let the same underlying Sharpe edge clear the MDD cap
without needing to retune the signal logic itself.

## Config Scan

Scaled `base_exposure=0.8*leverage_cap, sensitivity=0.9*leverage_cap` at
leverage_cap in {0.3, 0.35, 0.4}: leverage_cap=0.3 (base_exposure=0.24,
sensitivity=0.27) was the lowest cap that kept both BTC and ETH MDD under
0.25 while Sharpe stayed above 1.0 for both.

## Primary Config Validation (Step 7)

Config: `long_len=20, base_exposure=0.24, sensitivity=0.27, leverage_cap=0.3`.

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| BTC/USDT | 1.266 (pass) | 0.229 (pass) | 0.874 (pass) | 1.00 (pass) | 0.007 rel-std (pass) |
| ETH/USDT | 1.155 (pass) | 0.195 (pass) | 0.915 (pass) | 1.00 (pass) | 0.029 rel-std (pass) |

All 5 validators pass for BOTH BTC/USDT and ETH/USDT.

## Decision

**ACCEPT for crypto (BTC/ETH) at leverage_cap=0.3.** Combined with
2026-09-14-176 (QQQ+SPY at leverage_cap=1.0), the Ergodic Oscillator
sizing dial is now a fully-accepted strategy across all 4 symbols tested
this trigger, at asset-class-appropriate leverage caps (equity 1.0x,
crypto 0.3x).
