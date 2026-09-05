# Growth/Value (IVW/IVE) Ratio SMA Regime Filter — Backtest Report

**Date:** 2026-09-05
**Strategy file:** `strategies/2026-09-05_ivw_ive_growth_value_regime.py`
**KB id:** 2026-09-05-068

## Hypothesis

Per ETFreplay's "Regime Change" blog (etfreplay.com/blog/regime-change/):
"Using a ratio of Growth to Value securities naturally shows which of
these two market segments is the strongest. When Growth outperforms
Value the ratio will rise." Source's methodology: hold the numerator
when the ratio is above its own N-month moving average; source found a
4-month MA (~80 trading days) best on their SCHG/FNDX sample. This repo
operationalizes it as a binary long/flat gate on the underlying (QQQ/SPY)
using the standard large-cap Growth/Value ETF pair IVW/IVE (S&P 500
Growth/Value, longer available history). First Growth/Value-ratio
strategy in this repo.

## Step 6 — Grid test (ma_window x QQQ/SPY/BTC/ETH x 3 vol regimes)

- param_grid: `ma_window=[50,80,120]`
- symbols: equity `[QQQ, SPY]`, crypto `[BTC/USDT, ETH/USDT]`
- vol_regime_splits=3
- 36 total cells, 9 passed (pass_fraction = 0.25)
- by_asset_class: equity 9/18; crypto 0/18 (decisive fail)
- by_vol_regime: low 6/12; mid 3/12; high 0/12
- best full-regime config: QQQ ma_window=50 (2/3 regimes pass: low 2.62, mid 1.41, high fails 0.51)

## Step 7 — Single-config validators (ma_window=50)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full period) | **1.14 — PASS** | 0.95 — FAIL (near-miss) | >= 1.0 |
| Max drawdown | 0.286 — FAIL | 0.341 — FAIL | <= 0.25 |
| Transaction cost survival (10bps/trade, 55 trades) | **1.09 — PASS** | **0.89 — PASS** | net Sharpe >= 0.5 |
| Walk-forward (4-split, manual fallback) | **1.00 — PASS** | **1.00 — PASS** | >= 0.75 |
| Parameter sensitivity | **0.085 — PASS** | **0.064 — PASS** | <= 0.5 |

QQQ is a genuine near-miss: 4/5 validators pass cleanly (Sharpe 1.14,
strong walk-forward, low parameter sensitivity, robust transaction-cost
survival with only 55 round trips), but max drawdown at 28.6% exceeds the
25% budget (driven mostly by the 2022 rate-hike drawdown, where the
Growth/Value regime filter apparently did not de-risk fast enough). SPY
fails both Sharpe (0.95, itself a near-miss) and max drawdown (34.1%).

## Step 8 — Decision: **REJECT (near-miss on QQQ MDD)**

All-validators-pass is required for accept. QQQ fails only max drawdown
(28.6% vs 25%) while every other validator passes cleanly -- flagged as a
near-miss worth revisiting with either a tighter MDD-triggered exit
overlay or a wider ma_window. SPY fails both Sharpe and MDD, not a
near-miss. Crypto is a decisive 0/18 grid fail. Strategy/report kept as a
record of this near-miss attempt.
