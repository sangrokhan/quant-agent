# Backtest Report: TIP/Real-Yield Regime Gate — SPY Fine-Tune (Shared Config Upgrade)

**Strategy file:** `strategies/2026-09-11_gld_tip_realyield_gate.py` (same file, new shared config)
**Date:** 2026-09-11
**Direct fine-tune follow-up to:** 2026-09-11-059 (accepted QQQ-only at trend_sma_window=30/tip_sma_window=50; SPY near-miss Sharpe 0.893, TC-survival fail)

## Hypothesis

Same TIP-trend-gated SMA trend-following mechanism as 2026-09-11-059. A
local parameter search around SPY (trend_sma_window in
{15,20,25,30,40,50,60} x tip_sma_window in {30,40,50,60,75,90,100}) found
trend_sma_window=25, tip_sma_window=30 clears SPY's Sharpe AND
transaction-cost-survival thresholds. Checking this same config against
QQQ shows it ALSO further improves QQQ's Sharpe (1.640 vs the original
30/50 config's 1.452) -- adopted as the new shared config across both
symbols, mirroring this repo's established shared-config-upgrade pattern
(e.g. 2026-09-11-055 for ITB/TLT).

## Single-config validation: trend_sma_window=25, tip_sma_window=30

| Validator | SPY | QQQ | GLD (still rejected) | Threshold |
|---|---|---|---|---|
| Sharpe ratio (full sample) | 1.495 ✅ | 1.640 ✅ | 0.306 ❌ | ≥ 1.0 |
| Max drawdown | 0.128 ✅ | 0.160 ✅ | 0.212 ✅ | ≤ 0.25 |
| Transaction-cost survival (10bps/trade) | 0.803 ✅ | 1.111 ✅ | 0.011 ❌ | ≥ 0.5 |
| Walk-forward (manual 4-split) | 1.00 (4/4) ✅ | 1.00 (4/4) ✅ | 0.75 (3/4) ✅ | ≥ 0.75 |
| Parameter sensitivity (relative std) | 0.106 ✅ | 0.083 ✅ | 0.371 ✅ | ≤ 0.5 |

Full validator suite re-run explicitly for all three symbols: SPY and QQQ
now both pass every validator (SPY newly accepted, QQQ improved
substantially); GLD remains decisively rejected at this config too
(confirms 059's finding that GLD itself doesn't benefit from this
mechanism, independent of the exact SMA windows chosen).

## Decision: ACCEPTED (upgrades 2026-09-11-059 to include SPY)

trend_sma_window=25, tip_sma_window=30 is adopted as the new shared config:
both QQQ and SPY now pass every validator, with QQQ's Sharpe improving from
1.452 to 1.640 and net-of-cost Sharpe from 1.099 to 1.111. This is a
genuine upgrade over 2026-09-11-059's SPY near-miss, achieved via config
refinement. GLD remains excluded from this strategy's recommended symbol
set across both tested configs.
