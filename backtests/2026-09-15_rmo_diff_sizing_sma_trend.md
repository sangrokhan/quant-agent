# Rahul Mohindar Oscillator (RMO) ST2-ST3 Diff Continuous Sizing — Backtest Report

**Date:** 2026-09-15
**Strategy ID:** 2026-09-15-019 (assigned in knowledge_base log)
**File:** `strategies/2026-09-15_rmo_diff_sizing_sma_trend.py`

## Hypothesis

Rahul Mohindar Oscillator (Viratech India, MetaStock 2006): 10-chained-SMA
bias line RMO = Close - MA_10, ST2 = EMA(RMO,st2_span), ST3 =
EMA(ST2,st3_span). Formula reused from repo's own already-confirmed
implementation (strategies/2026-09-05_rmo_swingline_regime_crossover.py,
sourced from trendsandbreakouts.com). Repo has 1 prior RMO entry, a binary
ST2/ST3-crossover-within-zero-line-regime trigger (accepted QQQ only, SPY
near-miss, crypto decisively rejected). This iteration reframes the ST2-ST3
swing-line spread as a CONTINUOUS SIZING dial: rolling z-scored +
tanh-squashed to [-1,1], used as a sizing multiplier within an
SMA(trend_window) uptrend gate, deadband to cut turnover, leverage_cap for
crypto. First RMO continuous-sizing variant in this repo.

## Grid test summary (Step 6)

`param_grid={st2_span: [20,30,45], zscore_window: [100,150], sensitivity:
[0.4,0.6], deadband: [0.2,0.35]}`, symbols QQQ/SPY (equity) +
BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 288, **passed:** 174, **pass_fraction:** 0.604.
- **by_asset_class:** equity 93/144 (0.646), crypto 81/144 (0.563).
- **by_vol_regime:** low 92/96 (0.958), mid 45/96 (0.469), high 37/96 (0.385).
- **best_cell:** QQQ, st2_span=20/zscore_window=150/sensitivity=0.4/
  deadband=0.35, low-vol, Sharpe 2.566.

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | st2_span=20/zscore_window=150/sensitivity=0.4/deadband=0.35 | 1.340 (pass) | 0.104 (pass) | 0.917 (pass, 139 trades) | 1.000 (pass) | 0.056 (pass) | **accepted** |
| SPY | st2_span=20/zscore_window=100/sensitivity=0.4/deadband=0.35 | 1.186 (pass) | 0.069 (pass) | 0.774 (pass, 109 trades) | 1.000 (pass) | 0.062 (pass) | **accepted** |
| BTC/USDT | st2_span=45/zscore_window=150/sensitivity=0.4/deadband=0.2, leverage_cap=0.4 | 0.127 (**fail**) | 0.274 (**fail**) | -0.059 (**fail**, 5677 trades) | 1.000 (pass) | 0.038 (pass) | **rejected** |
| ETH/USDT | st2_span=30/zscore_window=150/sensitivity=0.4/deadband=0.2, leverage_cap=0.4 | 0.154 (**fail**) | 0.309 (**fail**) | -0.054 (**fail**, 5801 trades) | 0.750 (pass) | 0.111 (pass) | **rejected** |

Walk-forward used manual 4-way `np.array_split` (repo's `check_walk_forward`
calls `vbt.utils.splitting.RangeSplitter`, unavailable in installed
vectorbt -- known recurring fix this cron trigger).

## Decision

**Accepted (QQQ + SPY):** both clear all 5 validators with strong margins
(TC-survival net Sharpe 0.77-0.92) -- also rescues the prior binary-
crossover entry's SPY near-miss rejection (2026-09-05-004).
**Rejected (BTC/USDT, ETH/USDT):** decisive Sharpe/MDD/TC-survival failures
driven by excessive turnover on the crypto loader's hourly bars (5,677-
5,801 trades over the full sample) -- same recurring pattern seen this
cron trigger with other sizing dials on crypto's higher-frequency data.
