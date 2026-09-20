# 2026-09-21 Volatility-Normalized "Overreaction" Momentum Continuation

**Hypothesis:** A large single-day return relative to trailing realized
volatility ("overreaction", z-score of daily return >= 1.5-2.5) predicts
short-term momentum continuation over the next few days.

**Source:** https://arxiv.org/html/2602.18912v1 ("Overreaction as an
indicator for momentum in algorithmic trading: A Case of AAPL stocks",
Lis/Slepaczuk/Sakowski, Feb 2026). The paper's ML/Twitter-sentiment models
are infeasible with this repo's OHLCV-only data/loaders.py; this iteration
operationalizes their stated non-ML baseline finding ("classical behavioral
momentum effects dominate at intermediate frequencies") as a pure
vol-normalized daily-return threshold + short fixed-hold continuation bet.

**Strategy file:** `strategies/2026-09-21_volnorm_overreaction_momentum.py`

## Step 6 — Grid test summary (entry_z: [1.5, 2.0, 2.5] x hold_days: [2, 5], SPY/QQQ/BTC/ETH, vol terciles)

- total_cells: 72, passed_cells: 8, **pass_fraction: 0.111**
- by_asset_class: equity 7/36, crypto 1/36
- by_vol_regime: low 2/24, mid 6/24, **high 0/24**
- best_cell: entry_z=1.5, hold_days=5, QQQ, mid-vol regime, Sharpe=1.36
- worst_cell: entry_z=1.5, hold_days=2, SPY, high-vol regime, Sharpe=-1.27

Weak and narrow: best cell only clears the bar in one asset/vol-regime slice.

## Step 7 — Single-config validators (best cell: entry_z=1.5, hold_days=5, QQQ, full 2019-2026 sample)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | -0.087 | >= 1.0 |
| Max drawdown | **FAIL** | 0.297 | <= 0.25 |
| Transaction cost survival (10bps/trade, 248 trades) | **FAIL** | net Sharpe -0.387 | >= 0.5 |
| Walk-forward (manual 4-split; `RangeSplitter` broken, per repo convention) | **FAIL** | 0.5 (2/4) | >= 0.75 |
| Parameter sensitivity (entry_z sweep 1.5/2.0/2.5) | **FAIL** | relative std 1.01 | <= 0.5 |

Full-sample results are decisively negative across every validator, despite
one mid-vol-regime grid slice looking attractive (Sharpe 1.36) -- that cell
was not representative of the whole holding period; the strategy is highly
sensitive to `entry_z` (mean Sharpe across the sweep is itself negative,
-0.159) and racks up 248 trades over the sample, making transaction costs
decisive.

## Step 8 — Decision: **REJECTED**

All five validators failed on the primary (full-sample, best-grid-cell)
config. Grid test confirms the idea is narrow and unstable (11% pass
fraction, 0/24 high-vol-regime cells). Strategy file and this report are
kept as a record per RESEARCH_LOOP.md Step 8 (rejected attempt, not a live
strategy).
