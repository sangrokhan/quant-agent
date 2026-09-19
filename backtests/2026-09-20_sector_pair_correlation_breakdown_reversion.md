# Sector-pair correlation breakdown -> lagging-leg reversion (REJECTED)

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_sector_pair_correlation_breakdown_reversion.py`
**Source:** https://trendsandbreakouts.com/correlation-breakdown-trading

## Hypothesis
Two same-sector ETFs (or ETH/BTC as a crypto analogue) that normally
track each other closely occasionally decouple. When the rolling 60-day
Pearson correlation of daily returns z-scores an unusual departure
(<= -2.0 vs its own trailing 252-day mean/std) from the pair's own
correlation regime, and the primary leg is the one that lagged going
into the breakdown, the lagging leg tends to catch up (source's "Setup
one: the reversion trade"). Adapted to this repo's long-only single-leg
interface: buy the lagging primary leg on a correlation-breakdown
z-score trigger, exit on correlation-regime normalization or a
max-hold time-stop.

## Grid test summary

**Equity leg (XLF/XLK vs XLI secondary):** 108 cells (corr_window in
{40,60,90} x z_entry in {1.5,2.0,2.5} x max_hold_days in {15,20},
symbols XLF/XLK, vol_regime_splits=3, 2019-2026)
- pass_fraction: 0.028 (3/108)
- by_vol_regime: low 0/36, mid 3/36, high 0/36
- best_cell: XLK, corr_window=40, z_entry=2.0, max_hold_days=20, mid-vol, Sharpe 1.51
- worst_cell: XLK, corr_window=40, z_entry=2.5, max_hold_days=20, high-vol, Sharpe -1.44

**Crypto leg (ETH/USDT vs BTC/USDT secondary):** 54 cells (same param
grid, single symbol, vol_regime_splits=3, 2019-2026)
- pass_fraction: 0.259 (14/54)
- by_vol_regime: low 6/18, mid 8/18, high 0/18
- best_cell: ETH/USDT, corr_window=90, z_entry=2.0, max_hold_days=20, low-vol, Sharpe 1.62
- worst_cell: same config, high-vol, Sharpe -0.68

## Single-config validators (best crypto cell: ETH/USDT, secondary=BTC/USDT, corr_window=90, z_entry=2.0, max_hold_days=20, full 2019-2026 sample)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.204 | >= 1.0 | FAIL |
| Max drawdown | 0.472 | <= 0.25 | FAIL |
| Transaction cost survival (10bps, 10 trades) | 0.197 | >= 0.5 | FAIL |
| Walk-forward (manual 4-split, repo convention -- vbt.utils.splitting unavailable) | 0.5 (2/4 splits positive) | >= 0.75 | FAIL |

4 of 4 validators run failed decisively. The grid's per-vol-regime-slice
Sharpe values (best cell 1.62 in the low-vol tercile alone) do NOT hold
up when tested over the full 2019-2026 sample with realistic transaction
costs and drawdown accounting -- the strategy trades rarely (10 trades
over 7+ years on the best crypto config) and the few losing trades
dominate the full-period result. Equity legs performed even worse
(2.8% grid pass_fraction).

## Decision: REJECTED

Rejection reason: decisive full-sample failure on Sharpe, max drawdown,
transaction-cost survival, and walk-forward for the grid's best-passing
cell; low grid pass_fraction on both asset classes (equity 2.8%, crypto
25.9%), concentrated almost entirely in the mid/low-vol terciles with
zero high-vol-regime passes in either asset class.

## Notes for future loops
- The source article's own three setups (reversion trade, confirmation
  signal, hedge-break risk-management) may be more tradeable via Setup
  2 (confirmation-only regime filter combined with an existing trend
  signal) or Setup 3 (portfolio-hedge risk-management overlay) rather
  than Setup 1 (standalone reversion entry) tested here -- a future
  iteration could revisit those framings instead.
- This is distinct from all prior "rolling correlation" entries in this
  repo (2026-09-10-032 correlation-LEVEL regime gate, 2026-09-16-119/120
  Correlation Trend Indicator price-vs-linear-trend correlation,
  2026-09-04-083/2026-09-08-074/082 price-ratio Z-SCORE spread pairs
  trades) -- this is the first to z-score a rolling CORRELATION
  statistic itself as a breakdown-detection trigger.
