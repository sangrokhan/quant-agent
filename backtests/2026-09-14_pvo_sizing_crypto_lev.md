# Backtest Report: PVO Sizing Dial -- Crypto Leverage-Cap Follow-up

**Strategy file:** `strategies/2026-09-14_pvo_sizing_sma_trend.py` (same file, different params)
**Date:** 2026-09-14

## Hypothesis

Direct follow-up to 2026-09-14-177 (PVO continuous sizing dial, accepted
QQQ+SPY but crypto BTC/ETH decisively failed MDD at leverage_cap=1.0). Per
this cron trigger's repeatedly-confirmed leverage-cap-recalibration fix
pattern (TMF-124, Elder-Ray/Chaikin-Osc-125, Ergodic-178 same-cron-trigger
precedent): lowering leverage_cap for crypto (scaling
base_exposure/sensitivity proportionally down with it) should let the same
underlying Sharpe edge clear the MDD cap.

## Config Scan

Scaled `base_exposure=1.0*leverage_cap, sensitivity=0.3*leverage_cap` at
leverage_cap in {0.25...0.4}: leverage_cap=0.29 gave a comfortable margin
on both symbols (BTC MDD 0.235, ETH MDD 0.182, both well under 0.25).

## Primary Config Validation (Step 7)

Config: `fast_span=12, base_exposure=0.29, sensitivity=0.09,
trend_window=40, zscore_window=200, deadband=0.25, leverage_cap=0.29`.

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| BTC/USDT | 1.313 (pass) | 0.235 (pass) | 1.087 (pass) | 1.00 (pass) | 0.010 rel-std (pass) |
| ETH/USDT | 1.203 (pass) | 0.182 (pass) | 1.033 (pass) | 1.00 (pass) | 0.022 rel-std (pass) |

All 5 validators pass for BOTH BTC/USDT and ETH/USDT.

## Decision

**ACCEPT for crypto (BTC/ETH) at leverage_cap=0.29.** Combined with
2026-09-14-177 (QQQ+SPY at leverage_cap=1.0), the PVO sizing dial is now
accepted across all 4 symbols tested this trigger, at asset-class-appropriate
leverage caps (equity 1.0x, crypto 0.29x).
