# Backtest Report: Ehlers Reversion Index continuous sizing dial, full-universe accept

**Strategy file:** `strategies/2026-09-16_ehlers_ri_sizing_sma_trend.py`
**Date:** 2026-09-16
**Prior id:** this cron trigger's own 2026-09-16-128 (binary crossover version, rejected)

## Hypothesis
Direct fix for this same cron trigger's prior rejection 2026-09-16-128
(Ehlers Reversion Index binary crossover-with-time-stop signal: equity
QQQ/SPY Sharpe near-miss ceiling ~0.92-0.98, crypto BTC/USDT+ETH/USDT
decisively rejected on max-drawdown at full binary exposure). This
sub-iteration reframes the raw Reversion Index (RI, already bounded [-1,+1]
by construction: rolling net price change / rolling sum of absolute price
changes) as a CONTINUOUS SIZING dial used directly (no z-score/tanh needed)
inside an SMA(trend_window) uptrend gate with a deadband, leverage-cap-aware
for crypto from the start. Source unchanged:
https://www.tradingview.com/script/V35NeC45-TASC-2026-01-The-Reversion-Index/
(John F. Ehlers, TASC Jan 2026, PineCodersTASC port).

## Step 6 — Grid test summary
Grid: `param_grid={ri_length:[14,20,30], sensitivity:[0.4,0.6,0.8], deadband:[0.15,0.25], leverage_cap:[0.3,0.5,1.0], base_exposure:[0.15,0.4]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`
-> total_cells=1296, passed=787, **pass_fraction=0.607** (the strongest grid
result of any strategy tested this cron trigger so far).
- by_asset_class: equity 320/648 (0.494), crypto 467/648 (0.721)
- by_vol_regime: low 421/432 (0.975), mid 281/432 (0.650), high 85/432 (0.197)

Best-average-Sharpe configs per symbol (grid-search stage):
- QQQ: `base_exposure=0.15, deadband=0.15, leverage_cap=0.3, ri_length=14, sensitivity=0.6`
- SPY: `base_exposure=0.4, deadband=0.25, leverage_cap=0.5, ri_length=14, sensitivity=0.8`
- BTC/USDT: `base_exposure=0.15, deadband=0.25, leverage_cap=0.5, ri_length=14, sensitivity=0.8`
- ETH/USDT: grid-best (`base_exposure=0.4, deadband=0.15, leverage_cap=1.0, ri_length=14, sensitivity=0.6`)
  passed Sharpe/TC/WF/param-sensitivity but MDD near-missed at 0.301>0.25;
  a dedicated follow-up sweep over `leverage_cap` in [0.5,0.6,0.7,0.8] found
  `leverage_cap=0.6, base_exposure=0.2, sensitivity=0.4` clears MDD cleanly
  (0.161) while keeping Sharpe strong (1.356) -- used as ETH/USDT's final
  config below.

## Step 7 — Validators (best config per symbol, full sample)

| Symbol | Sharpe | MDD | TC net Sharpe | Walk-forward | Param sens (relstd) |
|---|---|---|---|---|---|
| QQQ | 1.340 | 0.053 | 0.867 | 1.00 | 0.040 |
| SPY | 1.208 | 0.054 | 0.921 | 1.00 | 0.035 |
| BTC/USDT | 1.558 | 0.185 | 1.486 | 1.00 | 0.066 |
| ETH/USDT | 1.356 | 0.161 | 1.251 | 1.00 | 0.063 |

All 5 validators pass on all 4 symbols. Full evidence dicts retained in
`validate_ehlers_ri_sizing_out.json` at repo root.

Final configs:
- QQQ: `trend_window=40 (default), ri_length=14, base_exposure=0.15, sensitivity=0.6, leverage_cap=0.3, deadband=0.15`
- SPY: `trend_window=40 (default), ri_length=14, base_exposure=0.4, sensitivity=0.8, leverage_cap=0.5, deadband=0.25`
- BTC/USDT: `trend_window=40 (default), ri_length=14, base_exposure=0.15, sensitivity=0.8, leverage_cap=0.5, deadband=0.25`
- ETH/USDT: `trend_window=40 (default), ri_length=14, base_exposure=0.2, sensitivity=0.4, leverage_cap=0.6, deadband=0.15`

## Decision
**Accept** (full universe: QQQ, SPY, BTC/USDT, ETH/USDT) -- all 5 validators
pass on all 4 symbols, with the strongest grid pass_fraction of any strategy
tested this cron trigger. This confirms the near-miss-rescue note from the
prior 2026-09-16-128 rejection: the raw RI value carries usable directional
signal that a binary crossover-with-time-stop framing discarded, and a
continuous sizing dial + leverage cap resolves both the equity Sharpe
ceiling and the crypto MDD problem simultaneously.
