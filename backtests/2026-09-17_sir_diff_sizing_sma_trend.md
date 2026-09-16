# Shinohara Intensity Ratio (SIR) — Continuous Sizing Dial — Backtest Report

**Hypothesis:** Direct follow-up to 2026-09-17-056 (SIR corrected formula
discrete crossover: SPY accepted, QQQ near-miss on parameter sensitivity
only). Applies this repo's standard "discrete near-miss -> continuous
sizing dial" fix: log(StrongRatio/WeakRatio) rolling z-scored and
tanh-squashed into a continuous [-1,1] exposure dial inside an
SMA(trend_window) uptrend gate with deadband, tested on the full
QQQ/SPY/BTC/USDT/ETH/USDT universe.

**Source:** Same ChartIQ SIR formula as 2026-09-17-056 (no new external
research this sub-iteration; standard sizing-dial transform pattern from
this repo's own prior successful rescues).

**Strategy file:** `strategies/2026-09-17_sir_diff_sizing_sma_trend.py`

## Step 6 — Grid test summary (param_grid: sir_window in [14,20,26] x
deadband in [0.05,0.1,0.2]; symbols: equity QQQ/SPY, crypto BTC/USDT,
ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 108, passed_cells: 36, **pass_fraction: 0.333**
- by_asset_class: equity 18/54 (33%), crypto 18/54 (33%) -- unusually
  even split, crypto looked promising in regime slices.
- by_vol_regime: low 24/36, mid 12/36, high 0/36.
- best_cell: sir_window=14, deadband=0.2, QQQ, low-vol regime, Sharpe=2.04.

## Step 7 — Single-config validators (full sample, best-looking grid configs)

| Validator | QQQ (sir_window=20, deadband=0.1) | SPY (same) | BTC/USDT (sir_window=26, deadband=0.1) | ETH/USDT (same) |
|---|---|---|---|---|
| Sharpe (>= 1.0) | **FAIL** 0.580 | **FAIL** 0.018 | **FAIL** 0.804 | **FAIL** 0.580 |
| Max Drawdown (<= 0.25) | PASS 0.212 | **FAIL** 0.252 | **FAIL** 0.580 | **FAIL** 0.508 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | **FAIL** -0.294 (1308 trades) | **FAIL** -0.427 (1328 trades) | **FAIL** 0.114 (1362 trades) | **FAIL** 0.091 (1359 trades) |
| Parameter sensitivity (relative_std <= 0.5, 20-cell sweep) | PASS 0.269 | **FAIL** 1.269 | PASS 0.183 | PASS 0.157 |

## Outcome: **REJECTED (all symbols, decisively on transaction-cost survival)**

Turnover is extreme (1300+ trades over ~7.5 years, roughly one trade
every 2 trading days) -- the deadband as configured does not meaningfully
suppress churn because `log(StrongRatio/WeakRatio)` is itself a noisy,
fast-moving ratio-of-rolling-sums that crosses the z-score deadband
threshold constantly even at deadband=0.2. This is the same "grid
regime-slices look attractive, full-sample fails" pattern already
documented at 2026-09-17-055 (platinum/palladium ratio) this trigger --
reinforcing the notes-field caution added there. Not pursuing a
turnover-reduction fix (wider deadband / longer zscore_window) this
sub-iteration since the discrete-crossover version (2026-09-17-056)
already delivered a clean SPY accept and the QQQ near-miss is a
lower-priority target than starting a fresh external-research iteration.
