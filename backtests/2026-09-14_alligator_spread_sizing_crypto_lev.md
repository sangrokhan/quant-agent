# Backtest Report: Williams Alligator Sizing Dial -- Crypto Leverage-Cap Follow-up

**Strategy file:** `strategies/2026-09-14_alligator_spread_sizing_sma_trend.py` (same file, different params)
**Date:** 2026-09-14

## Hypothesis

Direct follow-up to 2026-09-14-182 (Alligator fan-spread sizing dial,
accepted QQQ+SPY but crypto BTC/ETH decisively failed MDD at
leverage_cap=1.0). Per this cron trigger's leverage-cap-recalibration fix
pattern (TMF-124, Elder-Ray/Chaikin-Osc-125, Ergodic-178, PVO-179,
KRI-181): lowering leverage_cap for crypto should let the same underlying
Sharpe edge clear the MDD cap.

## Config Scan

Scaled `base_exposure=1.0*leverage_cap, sensitivity=0.5*leverage_cap` at
leverage_cap in {0.25, 0.3, 0.35}: leverage_cap=0.25 was the lowest cap
tested that kept both BTC and ETH MDD comfortably under 0.25.

## Primary Config Validation (Step 7)

Config: `atr_window=14, base_exposure=0.25, sensitivity=0.12,
trend_window=40, leverage_cap=0.25`.

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| BTC/USDT | 1.237 (pass) | 0.205 (pass) | 0.904 (pass) | 1.00 (pass) | 0.013 rel-std (pass) |
| ETH/USDT | 1.141 (pass) | 0.216 (pass) | 0.911 (pass) | 0.75 (pass, exactly at threshold) | 0.024 rel-std (pass) |

All 5 validators pass for BOTH BTC/USDT and ETH/USDT (ETH walk-forward is
an exact-threshold pass: 3/4 quarters positive Sharpe).

## Decision

**ACCEPT for crypto (BTC/ETH) at leverage_cap=0.25.** Combined with
2026-09-14-182 (QQQ+SPY at leverage_cap=1.0), the Alligator fan-spread
sizing dial is now accepted across all 4 symbols tested this trigger, at
asset-class-appropriate leverage caps (equity 1.0x, crypto 0.25x).
