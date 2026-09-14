# Gann HiLo Activator Distance Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-159 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_gann_hilo_dist_sizing_sma_trend.py`

## Hypothesis

Gann HiLo Activator (per LuxAlgo/TradingPedia/Enlightened Stock Trading/
trendsandbreakouts.com): a trailing trend line built from two short-lookback
SMAs (`SMA_high = SMA(High,N)`, `SMA_low = SMA(Low,N)`) that flips between
following the low-average (uptrend support) and the high-average (downtrend
resistance) based on close crossing the current line value. This is a NEW
indicator family for this repo (0 prior entries of any kind). This
iteration uses the normalized distance between price and whichever
reference SMA is currently "active" per the flip state machine, `(Close -
Line) / Line`, as a CONTINUOUS SIZING dial: rolling z-scored +
tanh-squashed to [-1,+1], sized within an SMA(trend_window) uptrend gate.
First Gann HiLo entry of any kind in this repo.

Source: https://www.luxalgo.com/library/indicator/gann-hilo-activator/
(via browser_exec — web_search's DuckDuckGo backend failed with a TLS
connection error for this query), cross-referenced with TradingPedia/
Enlightened Stock Trading descriptions shown inline in Google results.

## Grid test summary (Step 6)

`param_grid={gann_window: [5,10,13], sensitivity: [0.5,0.7]}`, symbols
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 72, **passed:** 35, **pass_fraction:** 0.486.
- **by_asset_class:** equity 18/36 (0.5), crypto 17/36 (0.472).
- **by_vol_regime:** low 23/24 (0.958), mid 10/24 (0.417), high 2/24 (0.083).
- **best_cell:** QQQ, gann_window=5/sensitivity=0.5, low-vol, Sharpe 2.72.
- **worst_cell:** QQQ, gann_window=5/sensitivity=0.5, high-vol, Sharpe -0.29.

## Single-config validator results (Step 7)

Best grid config (gann_window=5, sensitivity=0.5) tested per symbol.
Equity (QQQ/SPY) failed decisively on TC-survival at default deadband=0.20
(428-434 trades) -- attempted rescue via wider deadband (0.3/0.4/0.5) but
QQQ's net-of-cost Sharpe never cleared 0.5 (best attempt at deadband=0.4:
gross Sharpe 0.992 near-miss, net Sharpe 0.389 still fails), so equity was
left at default params and rejected outright. Crypto: BTC/USDT passed
outright; ETH/USDT needed leverage_cap reduced from 0.4 to 0.25 to clear
max-drawdown (0.292 -> 0.202):

| Symbol | Config | Trades | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|---|
| QQQ | default | 428 | 0.868 (**fail**) | 0.143 (pass) | 0.007 (**fail**) | 1.0 (pass) | 0.082 (pass) | **rejected** |
| SPY | default | 434 | 0.842 (**fail**) | 0.114 (pass) | -0.113 (**fail**) | 1.0 (pass) | 0.127 (pass) | **rejected** |
| BTC/USDT | lev_cap=0.4 | 270 | 1.438 (pass) | 0.220 (pass) | 1.001 (pass) | 1.0 (pass) | 0.022 (pass) | **accepted** |
| ETH/USDT | lev_cap=0.25 | 229 | 1.217 (pass) | 0.202 (pass) | 0.825 (pass) | 1.0 (pass) | 0.014 (pass) | **accepted** |

## Decision

**Accepted (crypto only):** BTC/USDT (leverage_cap=0.4), ETH/USDT
(leverage_cap=0.25) — all 5 validators pass.
**Rejected (equity):** QQQ, SPY — both fail Sharpe AND TC-survival at
default settings; a deadband-widening rescue attempt (that worked for
FRAMA earlier this cron trigger) did not clear the TC-survival threshold
here, so this indicator's raw distance metric appears to have structurally
higher turnover on equity daily bars than most of this run's other
overlays.

Scope note: Gann HiLo distance continuous-sizing dial only holds up on
crypto (BTC/ETH); equity rejection is decisive, not a near-miss.

Full raw grid: `/tmp/gann_grid_summary.json` (not committed, ephemeral).
Full raw validators: `validators_gann_hilo_dist_sizing.json`.
