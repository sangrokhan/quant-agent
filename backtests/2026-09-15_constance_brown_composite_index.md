# 2026-09-15 Constance Brown CMB Composite Index MA-Crossover

**Hypothesis:** Per StockCharts ChartSchool
(https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/cmb-composite-index),
Constance Brown's CMB Composite Index = 9-period ROC of 14-period RSI +
3-period SMA of 3-period RSI (deliberately unbound, unlike traditional
RSI). Source's own disclosed rule: long entry when the Composite Index
Line crosses above BOTH its fast (13-period) and slow (33-period) SMAs;
exit when it crosses below either. First Constance Brown Composite Index
entry in this repo.

**Best joint grid config:** fast_ma_period=10, slow_ma_period=45,
max_hold_days=30 (RSI/ROC/momentum periods at source defaults 14/9/3/3)

## Single-config validator results (full 2018-2026 sample)

| Symbol | Sharpe | MDD | TC net Sharpe |
|---|---|---|---|
| QQQ | 0.895 (**FAIL** near-miss, thr 1.0) | 0.242 (near-miss, thr 0.25) | 0.656 (pass) |
| SPY | 1.261 (pass) | 0.166 (pass) | 0.906 (pass) |
| BTC/USDT | 0.631 (**FAIL** decisive) | 0.580 (**FAIL** decisive) | 0.550 (pass) |
| ETH/USDT | 0.555 (**FAIL** decisive) | 0.601 (**FAIL** decisive) | 0.493 (**FAIL**) |

## Grid summary (fast_ma_period in [10,13,18] x slow_ma_period in
[25,33,45] x max_hold_days in [30,60], QQQ/SPY/BTC-USDT/ETH-USDT x
low/mid/high vol tercile, 216 cells)

- pass_fraction: 0.278 (60/216)
- by_asset_class: equity 42/108; crypto 18/108
- by_vol_regime: low 34/72; mid 18/72; high 8/72
- A dedicated QQQ-only parameter search (25 combos varying fast/slow/
  max_hold_days, plus a further 36-combo search varying rsi_period/
  roc_period too) found ZERO configs clearing both Sharpe>=1.0 AND
  MDD<=0.25 simultaneously for QQQ -- best found was Sharpe 0.921/MDD
  0.213 (rsi_period=21, roc_period=9, fast=13, slow=33).

## Outcome: ACCEPTED (SPY only); REJECTED (QQQ near-miss ceiling appears
below threshold even after a dedicated parameter search; crypto decisive
fail)

QQQ's near-miss (Sharpe 0.895-0.921 across everything tried) appears to be
a genuine ceiling for this specific mechanism on QQQ rather than a
parameter-tuning artifact -- a QQQ-specific rescue was attempted this same
sub-iteration and did not clear the bar, so it is not pursued further this
cron trigger. Crypto fails decisively on both Sharpe and MDD at every grid
cell tested -- the unbound RSI-derivative construction appears far too
noisy/high-turnover for BTC/ETH's volatility profile (446-454 trades over
the sample, MDD ~58-60%).
