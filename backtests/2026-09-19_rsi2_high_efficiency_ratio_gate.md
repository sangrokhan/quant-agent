# RSI(2) Mean-Reversion + High Efficiency-Ratio Gate — QQQ Accepted (2026-09-19)

**Hypothesis:** Cesar Alvarez's "Efficiency Ratio and Mean Reversion"
(https://alvarezquanttrading.com/blog/efficiency-ratio-and-mean-reversion/,
read via browser_exec after web_search DDGS backend returned unusable
results this iteration) found the counter-intuitive result that requiring
a HIGH Kaufman Efficiency Ratio (ER >= 20, i.e. a comparatively clean/
efficient recent price move rather than pure noise) on the mean-reversion
setup day improved every major metric on two of his own tested
mean-reversion portfolios. This strategy adds that exact ER >= threshold
gate to this repo's already-accepted Connors RSI(2) mean-reversion
strategy (`strategies/2026-09-03_rsi2_meanrev_trend200.py`, id
2026-09-03-005), implemented as a new sibling file
`strategies/2026-09-19_rsi2_high_efficiency_ratio_gate.py`.

## Step 6 grid summary

Grid: `rsi_entry` in {5, 10} x `er_threshold` in {0, 20, 40} x
`trend_window`={200}, QQQ+SPY (equity) + BTC/USDT+ETH/USDT (crypto),
vol_regime_splits=3.

- total_cells: 72, passed_cells: 22, **pass_fraction: 0.306**
- by_asset_class: equity 18/36 (50.0%), crypto 4/36 (11.1%)
- by_vol_regime: low 11/24, mid 9/24, high 2/24
- best_cell: rsi_entry=10, er_threshold=20, QQQ, low-vol tercile, Sharpe 2.539
- worst_cell: rsi_entry=5, er_threshold=20, SPY, high-vol tercile, Sharpe -0.530

Full raw grid: `grid_result_rsi2_high_er.json`.

## Step 7 single-config validation (rsi_entry=10, er_threshold=20, trend_window=200)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.070 (PASS) | 1.035 (PASS) | >= 1.0 |
| Max drawdown | 0.071 (PASS) | 0.085 (PASS) | <= 0.25 |
| Transaction cost survival (10bps/trade) | net Sharpe 0.762 (PASS) | net Sharpe 0.620 (PASS) | >= 0.5 |
| Walk-forward (4 splits) | 4/4 positive (PASS) | 2/4 positive, **0.5 (FAIL)** | >= 0.75 |
| Parameter sensitivity (er_threshold x rsi_entry 3x3 grid) | CV=0.165 (PASS) | CV=0.154 (PASS) | <= 0.5 |

Full raw validators: `validators_rsi2_high_er.json`.

## Decision: ACCEPTED (QQQ only); REJECTED (SPY — walk-forward fail); REJECTED (crypto — decisive, 4/36 grid cells)

QQQ clears all 5 validators cleanly, including an excellent MDD (0.071)
consistent with the ER filter's reported effect of raising trade quality
(90 trades over 7.5y — a meaningfully larger, statistically more credible
sample than several of this repo's prior RSI(2)/mean-reversion near-miss
entries). SPY's first two of four walk-forward splits are negative despite
passing every other validator, so SPY is rejected per Step 8's
all-validators-pass rule. Crypto's grid pass fraction (4/36, concentrated
narrowly) is consistent with this repo's broad pattern of RSI(2)/mean-
reversion strategies not transferring to crypto's different volatility/
trend regime, and was not further validated given the decisive grid
signal.
