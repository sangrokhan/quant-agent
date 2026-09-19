# 1D Kalman-Filter Trend Direction — REJECTED

**Hypothesis:** Per Alphrex's "Kalman Filter Trend" strategy page
(https://alphrex.com/strategies/kalman), a 1D Kalman filter treats the
true latent log-price trend as a hidden state observed through noisy
price measurements (state x(t)=x(t-1)+w, obs z(t)=x(t)+v), with an
adaptive Kalman gain optimally weighting prior prediction vs new
observation. Alphrex's disclosed default parameters: process_noise (Q) =
0.0001, obs_noise (R) = 0.01. Trading rule: long when the filtered
state's period-over-period change is positive, short when negative.
First Kalman-filter-based strategy in this repo (zero prior entries).

## Step 6 — Grid test summary

Grid: `process_noise` in {0.0001, 0.001, 0.01} x `obs_noise` in
{0.01, 0.05}, symbols equity={SPY,QQQ} crypto={BTC/USDT,ETH/USDT},
vol_regime_splits=3. 72 total cells.

- `pass_fraction`: 8/72 = **0.111**
- `by_asset_class`: equity 8/36 passed, **crypto 0/36**
- `by_vol_regime`: low 7/24, mid 1/24, **high 0/24**
- `best_cell`: process_noise=0.0001, obs_noise=0.05, ETH/USDT, mid-vol
  regime, Sharpe=2.47 (crypto, despite crypto's overall 0/36 pass rate —
  a single lucky cell, not representative)
- `worst_cell`: process_noise=0.01, obs_noise=0.01, QQQ, high-vol regime,
  Sharpe=-1.39

## Step 7 — Single-config validation (best equity full-sample config:
QQQ, process_noise=0.0001, obs_noise=0.05, full sample 2018-01 to
2026-09)

Full-sample Sharpe across ALL 6 param combos tested on both SPY and QQQ
ranged from -0.49 to +0.33 -- never approaching the 1.0 threshold at any
setting, with max drawdowns consistently in the 38-76% range (the
strategy is ALWAYS in the market, long or short, never flat, so it fully
absorbs every drawdown with no risk-off state).

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 0.334 | >= 1.0 | **FAIL** |
| Max drawdown | 0.420 | <= 0.25 | **FAIL** |
| Tx-cost survival (5bps/trade, 162 trades) | net Sharpe 0.285 | >= 0.5 | **FAIL** |
| Parameter sensitivity (6-cell process_noise x obs_noise sweep) | relative_std 7.80 | <= 0.5 | **FAIL** |

(Walk-forward validator skipped this iteration given the decisive
full-sample failure across every grid config already tested — running it
would not change the accept/reject decision.)

Parameter sensitivity is extremely unstable (relative_std 7.80, ~16x the
threshold) — the strategy's Sharpe flips sign and magnitude wildly across
nearby Q/R settings, consistent with the source's own documented failure
mode ("wrong [Q/R] values give systematically over- or under-reactive
filters... without careful calibration, Kalman filter trading signals can
underperform simple moving averages").

## Decision: REJECTED

4 of 4 validators run fail decisively. The always-in-market long/short
construction (no flat state) means every whipsaw and reversal is fully
absorbed, producing large drawdowns regardless of Q/R tuning. This
confirms the source's own documented caveat that Kalman filter trend
signals require careful empirical Q/R calibration (e.g. via
expectation-maximization) to avoid underperforming simple moving
averages — the disclosed "default" parameters do not work out of the box
on SPY/QQQ/BTC/ETH daily bars. Strategy file kept in `strategies/` as a
record of a rejected attempt (not live).
