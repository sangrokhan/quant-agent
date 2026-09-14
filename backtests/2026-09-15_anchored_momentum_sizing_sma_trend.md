# Anchored Momentum Continuous Sizing — Backtest Report

**Date:** 2026-09-15
**Strategy ID:** 2026-09-15-017 (assigned in knowledge_base log)
**File:** `strategies/2026-09-15_anchored_momentum_sizing_sma_trend.py`

## Hypothesis

Anchored Momentum (Rudy Stefenel, TASC 1998): momentum = EMA(ema_period,
close) / SMA(sma_period, close) - 1, a percentage-difference construction
that replaces the noisy two-point momentum calc with a smoother anchor.
Confirmed via https://doc.stocksharp.com/api-examples/1944_AnchoredMomentum.html
(visited this iteration, browser_exec fallback -- web_search's DDGS backend
has been unreliable this cron trigger). Already zero-centered by
construction. Repo has 1 prior entry (2026-09-06-177, binary
threshold-crossover, accepted QQQ only). This iteration reframes it as a
CONTINUOUS SIZING dial: rolling z-scored + tanh-squashed to [-1,1], used as
a sizing multiplier within an SMA(trend_window) uptrend gate, deadband to
cut turnover, leverage_cap for crypto. First Anchored Momentum
continuous-sizing variant in this repo.

## Grid test summary (Step 6)

`param_grid={ema_period: [6,12,20], sma_period: [8,20,30], sensitivity:
[0.4,0.6], deadband: [0.2,0.35]}`, symbols QQQ/SPY (equity) +
BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 432, **passed:** 229, **pass_fraction:** 0.530.
- **by_asset_class:** equity 117/216 (0.542), crypto 112/216 (0.519).
- **by_vol_regime:** low 137/144 (0.951), mid 64/144 (0.444), high 28/144 (0.194).
- **best_cell:** QQQ, ema_period=12/sma_period=30/sensitivity=0.6/
  deadband=0.35, low-vol, Sharpe 2.774.
- **worst_cell:** ETH/USDT, ema_period=12/sma_period=8/sensitivity=0.6/
  deadband=0.35, high-vol, Sharpe -0.742.

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | ema_period=6/sma_period=20/sensitivity=0.4/deadband=0.35 | 1.255 (pass) | 0.091 (pass) | 0.908 (pass, 121 trades) | 1.000 (pass) | 0.316 (pass) | **accepted** |
| SPY | ema_period=6/sma_period=20/sensitivity=0.4/deadband=0.35 | 1.223 (pass) | 0.062 (pass) | 0.892 (pass, 96 trades) | 1.000 (pass) | 0.161 (pass) | **accepted** |
| BTC/USDT | ema_period=6/sma_period=20/sensitivity=0.6/deadband=0.2, leverage_cap=0.4 | 0.132 (**fail**) | 0.304 (**fail**) | -0.058 (**fail**, 5607 trades) | 1.000 (pass) | 0.311 (pass) | **rejected** |
| ETH/USDT | ema_period=20/sma_period=20/sensitivity=0.6/deadband=0.2, leverage_cap=0.4 | 0.221 (**fail**) | 0.268 (**fail**) | -0.049 (**fail**, 5943 trades) | 1.000 (pass) | 0.568 (**fail**) | **rejected** |

Walk-forward used manual 4-way `np.array_split` (repo's `check_walk_forward`
calls `vbt.utils.splitting.RangeSplitter`, unavailable in installed
vectorbt -- known recurring fix this cron trigger).

## Decision

**Accepted (QQQ + SPY):** both clear all 5 validators at ema_period=6/
sma_period=20/sensitivity=0.4/deadband=0.35 -- strong margin (TC-survival
net Sharpe ~0.9 on both), and a same-config rescue of the prior
binary-crossover entry's SPY rejection (2026-09-06-177 rejected SPY
decisively; this sizing-dial reframing passes SPY cleanly).
**Rejected (BTC/USDT, ETH/USDT):** decisive Sharpe/MDD/TC-survival failures
driven by excessive turnover on the crypto loader's hourly bars (5,607-
5,943 trades over the full sample) -- same recurring pattern seen this
cron trigger with other sizing dials on crypto's higher-frequency data.
