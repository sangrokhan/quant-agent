# VWMA vs SMA Crossover (Calhoun, TASC Feb 2017 article/Apr 2017 code) — Rejected

**Source:** https://traders.com/Documentation/FEEDbk_docs/2017/04/TradersTips.html
(Ken Calhoun, "Volume-Weighted Moving Average Breakouts", TASC Feb 2017
article / Apr 2017 Traders Tips code; TradeStation code disclosed)

**Hypothesis:** VWMA(50) compared against a plain SMA(70) of the same
price series. Source's own rule: buy when VWMA crosses over the SMA, exit
on the reverse cross. Distinct from this repo's existing VWMA(10) vs
VWMA(100) dual-VWMA crossover (2026-09-04-060, accepted) since only ONE
line here is volume-weighted while the other is a plain unweighted SMA.

## Grid summary (144 cells: 2 vwma_length x 3 ma_length x 2 max_hold_days
x 4 symbols x 3 vol regimes)

- pass_fraction: 0.25 (36/144)
- by_asset_class: equity 30/72, crypto 6/72
- by_vol_regime: low 26/48, mid 10/48, **high 0/48**
- best config by avg-Sharpe: QQQ, vwma_length=50, ma_length=100,
  max_hold_days=40 — 2/3 regimes passed, avg Sharpe 1.28

## Single-config validation (QQQ, vwma_length=50, ma_length=100,
max_hold_days=40)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.820 | >= 1.0 | FAIL |
| Max drawdown | 15.6% | <= 25% | PASS |
| TC survival (net Sharpe, 10 trades) | 0.802 | >= 0.5 | PASS |
| Walk-forward (4 splits) | 0.75 (3/4 positive) | >= 0.75 | PASS |
| Parameter sensitivity (relative std) | 0.609 | <= 0.5 | FAIL |

## Verdict: REJECTED

Full-sample Sharpe (0.820) and parameter sensitivity (0.609) both fail,
despite MDD/TC-survival/walk-forward passing. Only 10 trades over the full
sample. High-vol regime failed 0/48 across every symbol/config combination.
The single-VWMA-vs-plain-SMA construction does not add value over this
repo's existing dual-VWMA crossover (already accepted for QQQ+SPY) — mixing
one volume-weighted line with one unweighted line appears to be a strictly
weaker signal than comparing two volume-weighted lines at different speeds.
