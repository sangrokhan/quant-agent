# Ehlers FM-Demodulated Z3 Momentum ROC Crossover — Backtest Report

**Source:** https://traders.com/Documentation/FEEDbk_docs/2021/06/TradersTips.html
(TASC June 2021, John Ehlers "Creating More Robust Trading Strategies With
The FM Demodulator"), TradeStation EasyLanguage "Strategy With FM
Demodulator" section, read via browser_exec (web_search DDGS backend
returned zero results for the original discovery query this iteration).

**Hypothesis:** Adds RMS-normalization + hard-clip to the raw 2-bar price
derivative before the same Nyquist-zeroed Z3 integration / ROC-crossover
logic already tested as the "Simple Strategy" baseline (repo id
2026-09-17-161, accepted QQQ but failed universally in the high-vol
regime). The normalization targets that specific failure mode by making
signal magnitude vol-invariant across regimes.

## Step 6 grid summary
`sig_period` in {8,12,16} x `roc_period` in {1,3} x `max_hold_days` in
{15,20}, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto),
vol_regime_splits=3. 144 total cells.

- pass_fraction: 34/144 = 23.6%
- by_asset_class: equity 30/72 (41.7%), crypto 4/72 (5.6%)
- by_vol_regime: low 26/48 (54.2%), mid 8/48 (16.7%), **high 0/48 (0%)**
- best_cell: sig_period=12, roc_period=1, max_hold_days=15, SPY low-vol, Sharpe=2.15
- QQQ per-symbol: 19/36 passed; best avg-Sharpe config sig_period=12,
  roc_period=3, max_hold_days=20 (avg Sharpe 1.72 across 3 vol regimes,
  2/3 regimes pass)

The normalization did NOT fix the high-vol failure mode: 0/48 high-vol
cells pass, identical qualitative outcome to the un-normalized baseline
(2026-09-17-161 also failed 0/108 in high-vol). The RMS-normalization
changes trade timing/frequency but does not change the underlying
Nyquist-zeroed-integration mechanic's fundamental incompatibility with
high-vol regimes.

## Step 7 single-config validators (QQQ, sig_period=12, roc_period=3, max_hold_days=20)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.490 | >=1.0 | PASS |
| Max drawdown | 28.86% | <=25% | **FAIL** |
| Transaction cost survival (10bps/trade, 73 trades) | net Sharpe 1.403 | >=0.5 | PASS |
| Walk-forward (manual 4-split fallback) | 0.75 (3/4 splits positive) | >=0.75 | PASS |
| Parameter sensitivity (12-cell QQQ grid, relative std) | 0.302 | <=0.5 | PASS |

Also checked sig_period=16, roc_period=3, max_hold_days=20 (next-best avg
Sharpe config): Sharpe 1.270 (pass), MDD **26.72%** (fail, still over
25% threshold), net Sharpe after costs 1.189 (pass), walk-forward 4/4
splits positive (pass), param sensitivity 0.302 (pass, same grid).

Both of the two best-avg-Sharpe QQQ configs fail max_drawdown narrowly
(26.7%-28.9% vs 25% threshold) despite passing every other validator.

## Decision: REJECTED (QQQ; max_drawdown validator fails)

The strategy has a genuine positive edge (Sharpe consistently >1.0,
reasonable transaction-cost survival, stable walk-forward, low parameter
sensitivity) but exceeds the repo's 25% max-drawdown threshold across the
best-performing configs tested. Not accepted per Step 8 (all validators
must pass). SPY and crypto were not separately validator-tested given the
grid's clear equity>>crypto pattern (crypto pass_fraction only 5.6%) and
QQQ's own MDD failure already disqualifying the primary target.
