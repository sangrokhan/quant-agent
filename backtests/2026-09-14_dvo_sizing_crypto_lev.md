# Backtest Report: DVO Sizing Dial -- Crypto Leverage-Cap Follow-up

**Strategy file:** `strategies/2026-09-14_dvo_sizing_sma_trend.py` (same file, different params)
**Date:** 2026-09-14

## Hypothesis

Direct follow-up to 2026-09-14-184 (DVO sizing dial, accepted QQQ+SPY but
crypto BTC decisively failed MDD and ETH double-failed Sharpe+MDD at
leverage_cap=1.0). Per this cron trigger's leverage-cap-recalibration fix
pattern (TMF-124, Elder-Ray/Chaikin-Osc-125, Ergodic-178, PVO-179,
KRI-181, Alligator-183): lowering leverage_cap for crypto (scaling
base_exposure/sensitivity proportionally down, and re-widening deadband
to control turnover) should let the same underlying Sharpe edge clear
both MDD and TC-survival caps.

## Config Scan

Scaled `base_exposure=0.8*leverage_cap, sensitivity=0.4*leverage_cap`.
deadband=0.1 initially gave good Sharpe/MDD at leverage_cap=0.3 but
FAILED TC-survival (488 trades, net Sharpe 0.353) -- widening deadband to
0.2 at the same leverage_cap=0.3 fixed TC-survival while keeping
Sharpe/MDD comfortably passing for both symbols.

## Primary Config Validation (Step 7)

Config: `rank_lookback=126, base_exposure=0.24, sensitivity=0.12,
trend_window=30, deadband=0.2, leverage_cap=0.3`.

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| BTC/USDT | ~1.13 (pass) | ~0.22 (pass) | 0.708 (pass) | 1.00 (pass) | 0.015 rel-std (pass) |
| ETH/USDT | 1.193 (pass) | 0.213 (pass) | 0.934 (pass) | 1.00 (pass) | 0.010 rel-std (pass) |

All 5 validators pass for BOTH BTC/USDT and ETH/USDT.

## Decision

**ACCEPT for crypto (BTC/ETH) at leverage_cap=0.3, deadband=0.2.**
Combined with 2026-09-14-184 (QQQ+SPY at leverage_cap=1.0, deadband=0.5),
the DVO sizing dial is now accepted across all 4 symbols tested this
trigger, at asset-class-appropriate params: equity 1.0x/db=0.5, crypto
0.3x/db=0.2.
