# RSI(2) Mean-Reversion Gated by Katsanos Market-Risk Correlation Filter

**Hypothesis:** This repo's accepted RSI(2)/SMA(200) mean-reversion
baseline (2026-09-03-005) trades unconditionally whenever RSI(2) is
oversold in a long-term uptrend. Per Markos Katsanos' "A Low-Risk ETF
Trading Strategy" (TASC October 2026 Traders' Tips,
https://traders.com/Documentation/FEEDbk_docs/2026/10/TradersTips.html,
re-read this iteration), his disclosed `cond_market_risk` filter -- a
rolling correlation-with-benchmark regime confirmation -- was validated
earlier this cron trigger as a genuinely new gate mechanism on an SMA
trend-following base (id 2026-09-24-007, accepted QQQ+SPY). This iteration
tests the SAME gate mechanism on a DIFFERENT base strategy family (RSI(2)
oversold mean-reversion instead of SMA trend-following), to see whether
the correlation-regime confirmation generalizes across strategy TYPES.

Source URL: https://traders.com/Documentation/FEEDbk_docs/2026/10/TradersTips.html

## Step 6 Grid Summary

param_grid={rsi_oversold:[10.0,15.0,20.0], cor_min:[0.4,0.5,0.6],
max_hold_days:[10,15]}, symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]},
vol_regime_splits=3, 2019-01-01..2026-09-01: total_cells=216, passed=90,
pass_fraction=0.417 (this cron trigger's best pass fraction so far).
by_asset_class: equity 72/108 (66.7%), crypto 18/108 (16.7% -- notably
higher crypto pass rate than most trend strategies in this repo, though
full-sample crypto validation below turned out to have a zero-trade edge
case). by_vol_regime: low 42/72 (58.3%), mid 24/72 (33.3%), high 24/72
(33.3% -- unusually broad regime coverage vs most rejected/near-miss
strategies in this repo which concentrate almost entirely in low-vol).
best_cell: QQQ rsi_oversold=10.0/cor_min=0.4/max_hold_days=10, low-vol,
Sharpe 2.29.

## Single-Config Validation (Step 7)

**QQQ** (benchmark=SPY, rsi_oversold=10.0, cor_min=0.4, max_hold_days=10):
- Sharpe: 1.065 (>=1.0) PASS
- Max Drawdown: 0.096 (<=0.25) PASS
- Transaction cost survival (10bps/trade, 116 trades): net Sharpe 0.674 (>=0.5) PASS
- Walk-forward (4 splits): 1.0 pass fraction (>=0.75) PASS
- Parameter sensitivity (rsi_oversold/cor_min/max_hold_days neighborhood): relative_std 0.065 (<=0.5) PASS
- **ALL VALIDATORS PASS**

**SPY** (benchmark=QQQ, rsi_oversold=10.0, cor_min=0.4, max_hold_days=15):
- Sharpe: 1.364 (>=1.0) PASS
- Max Drawdown: 0.054 (<=0.25) PASS
- Transaction cost survival (10bps/trade, 119 trades): net Sharpe 0.719 (>=0.5) PASS
- Walk-forward (4 splits): 1.0 pass fraction (>=0.75) PASS
- Parameter sensitivity (rsi_oversold/cor_min/max_hold_days neighborhood): relative_std 0.244 (<=0.5) PASS
- **ALL VALIDATORS PASS**

**BTC/USDT:** full-sample check at the grid's best config (rsi_oversold=10.0,
cor_min=0.4, benchmark=ETH/USDT) produced ZERO trades over the full
2019-2026 sample (the market-risk gate combined with RSI(2)<10 oversold is
too restrictive an AND-gate to ever co-occur for BTC/USDT against this
benchmark over the full period, despite non-trivial grid-cell-slice
Sharpe values from the vol-regime-sliced grid test) -- not a real,
statistically meaningful result. REJECTED for crypto as infeasible/no-signal.

## Decision: ACCEPT (equity: QQQ + SPY, per-symbol tuned configs)

Both equity symbols clear all 5 validators cleanly on the FIRST config
tried (no rescue/retune needed) with excellent max-drawdown control
(9.6% and 5.4% respectively) thanks to the RSI(2) mean-reversion base's
inherently short holding periods combined with the correlation-regime
gate's additional selectivity. Crypto rejected for zero-trade infeasibility
at the full-sample level despite promising grid-cell-slice numbers --
a caution for future loops about over-trusting sliced-grid Sharpe values
without a full-sample sanity check.
