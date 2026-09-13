# Backtest Report: Multi-Horizon Donchian Ensemble + Volatility Targeting

**Strategy file:** `strategies/2026-09-14_donchian_ensemble_voltarget.py`
**Knowledge base id:** 2026-09-14-115

## Hypothesis

Source: https://www.quantifiedstrategies.com/crypto-trend-trading-strategy/
(summarizing Zarattini, Pagani & Barbon, "Catching Crypto Trends: A Tactical
Approach for Bitcoin and Altcoins"). Instead of a single-lookback Donchian
breakout, average breakout state across MANY lookback horizons (5, 10, 20,
30, 60, 90, 150, 250 days) into one ensemble fraction-long signal, then size
exposure via inverse realized-volatility targeting (target_annual_vol /
realized_vol, capped at leverage_cap). This repo has ~15 prior single-window
Donchian breakout entries, essentially all failing crypto decisively on MDD.
This iteration tests whether the multi-horizon ENSEMBLE construction (not a
new indicator, but diversification across window choice) is the structural
fix the source paper claims (reported BTC MDD 19% vs 80%+ buy-and-hold,
Sharpe 1.58, 2015-2025).

## Config tested (best/primary)

`donchian_windows=(5,10,20,30,60,90,150,250)`, `target_annual_vol=0.20`,
`vol_lookback=20`, `leverage_cap=1.0`, `deadband=0.15`

## Single-config validator results

| Validator | QQQ | SPY | BTC/USDT |
|---|---|---|---|
| Sharpe (>=1.0) | 1.093 PASS | 1.161 PASS | 0.234 FAIL |
| Max Drawdown (<=0.25) | 0.158 PASS | 0.130 PASS | 0.450 FAIL |
| TC survival (10bps/trade, net Sharpe >=0.5) | 0.799 PASS (156 trades) | 0.852 PASS (123 trades) | -0.027 FAIL (4807 trades) |
| Walk-forward (4 manual contiguous folds, >=0.75 pass frac) | 0.75 PASS (3/4) | 0.75 PASS (3/4) | 1.0 PASS (4/4) |
| Param sensitivity (target_annual_vol sweep 0.15/0.20/0.25, rel-std <=0.5) | 0.024 PASS | 0.007 PASS | 0.002 PASS (but base Sharpe already failing) |
| **All pass?** | **YES** | **YES** | **NO (Sharpe/MDD/TC all fail)** |

Note: `check_walk_forward` in `validation/validators.py` calls
`vbt.utils.splitting.RangeSplitter`, unavailable in installed vectorbt
1.1.0 -- used a manual contiguous 4-fold split instead (consistent with
prior iterations' documented workaround).

## Grid summary (Step 6)

`param_grid={target_annual_vol: [0.15,0.20,0.25], leverage_cap: [1.0,2.0],
deadband: [0.05,0.15]}`, `symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,
ETH/USDT]}`, `vol_regime_splits=3` (low/mid/high realized-vol terciles).

- total_cells=144, passed_cells=36, **pass_fraction=0.25**
- by_asset_class: equity 36/72 passed, **crypto 0/72 passed**
- by_vol_regime: low 24/48, mid 12/48, **high 0/48**
- best_cell: SPY, target_annual_vol=0.20, leverage_cap=1.0, deadband=0.15,
  low-vol regime, Sharpe=2.594
- worst_cell: QQQ, target_annual_vol=0.25, leverage_cap=2.0, deadband=0.05,
  high-vol regime, Sharpe=-0.555

## Decision: ACCEPT (equity QQQ + SPY only) / REJECT (crypto)

Equity (QQQ, SPY) passes all 5 validators cleanly at
target_annual_vol=0.20/leverage_cap=1.0/deadband=0.15, with very low
parameter sensitivity (rel-std 0.007-0.024) and 100% low-vol-tercile pass
rate. Crypto (BTC/USDT) fails decisively on Sharpe (0.234), MDD (45.0%>25%
threshold), and transaction-cost survival (net Sharpe -0.03 driven by 4807
trades over the sample -- the ensemble's multiple overlapping lookback
windows generate far more rebalancing turnover on crypto's higher-frequency
volatility than on equities, even with the deadband applied).

**This extends this repo's now-consistent finding (10/10 continuous-sizing
dials failed crypto MDD in the prior cron trigger) to a genuinely different
mechanism family (multi-horizon breakout ensemble + vol targeting, not a
single-indicator sizing dial) -- crypto still fails, and for largely the
same reason (MDD/turnover), reinforcing that the repo's SMA-trend-gate /
single-signal-family template itself, not just the specific indicator
choice, is the likely mismatch for crypto's regime characteristics.** A
future iteration should consider a structurally different crypto approach:
explicit regime-conditional leverage caps (hard leverage ceiling during
high-realized-vol terciles rather than continuous vol-targeting scaling),
or testing on a coarser rebalance frequency (weekly rather than daily) to
directly address the turnover-driven TC failure seen here.
