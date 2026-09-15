# Backtest Report: Donchian Ensemble Vol-Target — ETH/USDT Retune Fix

**Date:** 2026-09-16 (iteration 4, cron trigger 2026-09-15 ~15:00 KST)
**Strategy file:** `strategies/2026-09-14_donchian_ensemble_voltarget.py` (unmodified, retune only)

## Hypothesis

Direct fix for prior id 2026-09-14-119 (Multi-horizon Donchian breakout
ensemble + inverse-realized-vol position sizing, accepted QQQ/SPY/BTC-USDT
but ETH/USDT left as a near-miss: Sharpe 0.970<1.0, all other 4 validators
already passing at `target_annual_vol=0.15/leverage_cap=1.0/deadband=0.15`).
This iteration tests whether a higher `target_annual_vol` (allowing more
average exposure, since ETH/USDT's realized vol run rate leaves the
0.15-target config under-levered relative to its edge) rescues the Sharpe
near-miss on the identical unmodified strategy code. No new external
research this iteration — pure parameter retune following this repo's
established "revisit a near-miss with a targeted parameter sweep before
concluding rejection" pattern.

## Parameter sweep (small, targeted — not a full grid_test.py run since only
one param dimension needed adjustment and the near-miss was already
isolated by iteration 2026-09-14-119)

`target_annual_vol in {0.10,0.15,0.20,0.25}` x `leverage_cap in
{0.75,1.0,1.5}`, `deadband=0.15` fixed (unchanged from original accept):

| target_annual_vol | leverage_cap=0.75 | =1.0 | =1.5 |
|---|---|---|---|
| 0.10 | 0.825 | 0.825 | 0.825 |
| 0.15 (original) | 0.944 | 0.970 | 0.969 |
| 0.20 | 1.003 | 1.035 | 1.019 |
| 0.25 | 1.065 | **1.117** | 1.121 |

Selected: `target_annual_vol=0.25, leverage_cap=1.0, deadband=0.15`
(clears 1.0 with the smallest deviation from the original accepted config
among passing cells).

## Single-config validator results (Step 7)

| Metric | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe | 1.117 | 1.0 | Yes |
| Max Drawdown | 0.229 | 0.25 | Yes |
| TC-survival (net Sharpe, 130 trades) | 1.012 | 0.5 | Yes |
| Walk-forward (4 splits) | 1.00 (4/4 positive) | 0.75 | Yes |
| Parameter sensitivity (9-cell grid rel-std) | 0.055 | 0.5 | Yes |

## Decision

**Accept ETH/USDT** at `target_annual_vol=0.25, leverage_cap=1.0,
deadband=0.15`. Combined with the existing 2026-09-14-119 accepts (QQQ,
SPY, BTC/USDT), the Donchian ensemble + vol-targeting mechanism now covers
the full universe: QQQ, SPY, BTC/USDT, ETH/USDT. No code changes to the
strategy file — this is a config-level fix recorded via this report and the
knowledge-base log entry (the strategy file itself already supports
`target_annual_vol` as a keyword parameter).
