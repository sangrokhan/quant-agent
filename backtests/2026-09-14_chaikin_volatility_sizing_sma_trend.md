# Chaikin Volatility Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-172 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_chaikin_volatility_sizing_sma_trend.py`
**Status:** REJECTED (all 4 symbols) -- kept as a record per Step 8.

## Hypothesis

Chaikin Volatility (Marc Chaikin): CV = percentage rate-of-change of an
EMA-smoothed high-low range, already zero-centered by construction. This
repo has 2 prior Chaikin Volatility entries (2026-09-04-133, 2026-09-09-079),
BOTH using it as a BINARY threshold/zero-line-cross trigger, both rejected
across all symbols. This iteration reframes CV as a CONTINUOUS SIZING dial:
rolling z-scored + tanh-squashed to [-1,1], sized within an
SMA(trend_window) uptrend gate, deadband + leverage_cap for crypto. First
Chaikin Volatility continuous-sizing variant in this repo.

Source: repo's own prior confirmed formula (2026-09-04-133, 2026-09-09-079,
citing trendspider.com/Definedge Securities); no new external source this
iteration -- pure technique variant on an already-confirmed formula.

## Grid test summary (Step 6)

`param_grid={roc_window: [10,20], sensitivity: [0.4,0.6,0.8]}`, symbols
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 72, **passed:** 41, **pass_fraction:** 0.569.
- **by_asset_class:** equity 15/36 (0.417), crypto 26/36 (0.722).
- **by_vol_regime:** low 24/24 (1.000), mid 13/24 (0.542), high 4/24 (0.167).
- **best_cell:** SPY, roc_window=10/sensitivity=0.4, low-vol, Sharpe 3.037.
- **worst_cell:** QQQ, roc_window=20/sensitivity=0.8, high-vol, Sharpe -1.066
  (worst single-cell loss seen across this cron trigger's sizing-dial
  entries so far).

Note: unusually, crypto's grid pass_fraction (0.722) exceeds equity's
(0.417) here -- the opposite of nearly every other sizing-dial variant
this cron trigger. Full-sample single-config validation below shows this
doesn't hold up once transaction costs and parameter stability are checked.

## Single-config validator results (Step 7)

Best grid config (roc_window=10, sensitivity=0.4) tested full-sample per
symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 1.085 (pass) | 0.129 (pass) | 0.215 (**fail**, decisive) | 0.750 (pass) | 0.507 (**fail**) | **rejected** |
| SPY | 1.095 (pass) | 0.071 (pass) | 0.053 (**fail**, decisive) | 1.000 (pass) | 0.523 (**fail**) | **rejected** |
| BTC/USDT | 0.193 (**fail**, decisive) | 0.245 (pass) | -0.062 (**fail**) | 1.000 (pass) | 0.218 (pass) | **rejected** |
| ETH/USDT | 0.159 (**fail**, decisive) | 0.246 (pass) | -0.061 (**fail**) | 0.750 (pass) | 0.198 (pass) | **rejected** |

## Decision

**Rejected (all 4 symbols).** QQQ and SPY both clear Sharpe/MDD/walk-forward
individually but decisively fail transaction-cost survival (0.215 and 0.053
vs 0.5 threshold -- CV's rapid mean-reversion around its own rolling
z-score at roc_window=10 drives high trade frequency/turnover that erodes
net returns) AND fail parameter sensitivity (rel-std 0.507/0.523, just over
the 0.5 threshold -- CV's sizing dial is unusually unstable to roc_window/
sensitivity perturbation compared to every other sizing-dial variant
accepted this cron trigger, likely because CV itself is a rate-of-change of
an already-smoothed series, making it a "second derivative"-like quantity
more sensitive to window choice). Crypto fails Sharpe/TC-survival decisively
as usual. Unlike prior sizing-dial iterations this cron trigger, this one
found NO acceptable symbol -- a useful negative result: Chaikin Volatility's
own magnitude appears too noisy/parameter-sensitive to serve as a stable
sizing dial, unlike other already-zero-centered oscillators (KPO, Coppock,
Vortex diff-ratio) that passed with this same technique.
