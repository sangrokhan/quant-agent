# Schaff Trend Cycle (STC) Oversold-Recovery, Trend-Gated — Backtest Report

**Date:** 2026-09-23
**Strategy file:** `strategies/2026-09-23_stc_oversold_recovery_trend_gate.py`
**Outcome:** REJECTED (full-sample Sharpe below threshold on both equity symbols; TC-survival also fails)

## Hypothesis + source

Per QuantifiedStrategies.com's Schaff Trend Cycle explainer
(https://www.quantifiedstrategies.com/schaff-trend-cycle-indicator/, read
via `browser_exec` this iteration — `web_search`'s DDGS backend returned
low-quality Korean-localized SERP snippets for the initial discovery query,
so subsequent detail reads went straight to `browser_exec`), STC (Doug
Schaff, 1990s) is a cyclical/double-stochastic-smoothed MACD variant bounded
[0,100]. Source's own disclosed rule: "If the main trend is up and the STC
is emerging from the oversold region, rising above the 25 level, a buy
signal is generated." Implemented literally: `close > SMA(trend_window)`
(uptrend) AND STC crosses up through `stc_entry_level` (25) triggers a long;
exit on STC crossing back down through `stc_exit_level` (75), trend-filter
break, or a `max_hold_days` time-stop. First Schaff Trend Cycle strategy in
this repo (double-EMA-MACD + 2-stage %K/%D stochastic construction, distinct
from existing MACD-crossover/Ergodic-TSI/plain-stochastic entries).

## Grid summary (Step 6)

`run_strategy_grid`: `param_grid={stc_entry_level:[20,25,30], trend_window:[150,200], max_hold_days:[10,15,20]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01. 216 cells total.

- **pass_fraction: 0.245** (53/216)
- **by_asset_class:** equity 44/108 passed; crypto 9/108 passed
- **by_vol_regime:** low 35/72; mid 18/72; **high 0/72** (edge decisively concentrated in low/mid-vol terciles — high-vol regime kills it entirely)
- **best_cell:** SPY, stc_entry_level=20/trend_window=150/max_hold_days=15, low-vol tercile, Sharpe 2.04
- **worst_cell:** ETH/USDT, stc_entry_level=30/trend_window=150/max_hold_days=20, high-vol tercile, Sharpe -0.70

Best full-sample (non-tercile-split) config selected for single-config
validation: `stc_entry_level=25, trend_window=150, max_hold_days=15`
(highest cross-vol-regime consistency for BTC/USDT in the raw per-cell scan,
also a clean round-number config for equity).

## Single-config validators (QQQ, SPY; `stc_entry_level=25, trend_window=150, max_hold_days=15`, 2019-01-01 to 2026-09-01)

| Validator | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 0.558 | 0.600 | >= 1.0 | **FAIL** (both) |
| Max drawdown | 0.180 | 0.109 | <= 0.25 | pass (both) |
| TC survival (10bps/trade, ~61 trades) | 0.441 | 0.411 | >= 0.5 | **FAIL** (both) |
| Walk-forward (4 manual date splits — `vbt.utils.splitting.RangeSplitter` still broken in installed vectorbt, same repo-wide workaround used since 2026-09-03) | 3/4 splits positive (0.75) | 3/4 splits positive (0.75) | >= 0.75 | pass (both) |

## Decision (Step 8): REJECT

Full-sample Sharpe (0.56 QQQ, 0.60 SPY) misses the 1.0 threshold decisively
enough (not a near-miss in the ~0.9-0.98 range seen elsewhere in this repo)
that a vol-regime-gate rescue attempt was not pursued this iteration — the
grid's own `high`-vol-tercile 0/72 result already shows the edge is real but
narrow (low/mid-vol only), consistent with the full-sample blended Sharpe
sitting well under 1.0. Flagged in `notes` as a rescue candidate for a
future iteration given the strong low-vol-tercile Sharpe (best cell 2.04)
and the grid's honest 24.5% pass fraction (broader than many outright
rejects in this KB).
