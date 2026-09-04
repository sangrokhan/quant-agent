# PPO Signal-Line Crossover + Zero-Line Confirm (QQQ) — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_ppo_signal_crossover_zeroline.py`
**Source:** https://www.quantifiedstrategies.com/percentage-price-oscillator/
(paywalled AmiBroker code; crossover + zero-line-confirm logic replicated
from the article's plain-English description, not copied code)

## Hypothesis

PPO (100*(EMA12-EMA26)/EMA26) crossing above its 9-period EMA signal line
marks a bullish momentum shift; per the source, this is "confirmed" as a
genuine trend (not noise) when PPO is also above the zero line (fast EMA >
slow EMA). Exit on signal-line cross-down, zero-line break, or a
`max_hold_days` time-stop.

## Grid test (Step 6)

`param_grid={fast_window:[8,12,16], slow_window:[21,26,34], signal_window:[9],
max_hold_days:[10,15]}`, `symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- 216 cells total, 11 passed (pass_fraction = 5.1%)
- by_asset_class: equity 11/108, crypto 0/108 (crypto: total wipeout)
- by_vol_regime: low 10/72, mid 1/72, high 0/72
- best_cell: fast_window=16, slow_window=21, max_hold_days=15, QQQ, low-vol
  regime, Sharpe=1.39
- worst_cell: fast_window=8, slow_window=21, max_hold_days=15, QQQ, high-vol
  regime, Sharpe=-1.33

The grid's only passing cells cluster in equity low-vol terciles — the
best single cell (Sharpe 1.39) is a narrow slice, not representative of the
full-sample behavior (confirmed below).

## Single-config validation (Step 7) — QQQ, fast=16/slow=21/signal=9/max_hold=15 (grid-best)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio (full sample, 2019-2026) | **FAIL** | 0.17 | 1.0 |
| max_drawdown | pass | 12.5% | 25% |
| transaction_cost_survival (10bps/trade, 39 trades) | **FAIL** | net Sharpe 0.08 | 0.5 |
| walk_forward (4 manual date-slices; vectorbt splitter API unavailable in installed v1.1.0, same known issue as prior iterations) | **FAIL** | 2/4 splits positive (0.5) | 0.75 |
| parameter_sensitivity (18-cell QQQ grid, relative std of mean Sharpe) | **FAIL** | 0.85 | 0.5 |

## Decision: **REJECTED**

Full-sample Sharpe (0.17) is far below the grid-best-cell figure (1.39) —
the grid-best cell was cherry-picked from a single low-vol tercile with few
trades, and does not generalize across the whole sample or across parameter
neighbors (parameter sensitivity fails badly, relative std 0.85 vs 0.5
threshold). Transaction costs alone cut Sharpe from 0.17 to 0.08. Walk-forward
is also a near-coin-flip (2/4 splits positive). Crypto rejected decisively
(0/108 grid cells) — PPO signal+zero-line combo shows no edge on 24/7 markets
in this sample, consistent with several prior MACD-family rejections in this
repo (2026-09-04-100 MACD histogram inflection, 093 Chaikin Oscillator).
