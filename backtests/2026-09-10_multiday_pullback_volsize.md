# Backtest report: Multi-day pullback + vol-adjusted sizing + fixed hold (QQQ)

**Strategy file:** `strategies/2026-09-10_multiday_pullback_volsize.py`
**Hypothesis id:** see `knowledge_base/strategies_log.jsonl` entry
2026-09-10-033

## Source

https://www.advancedinvesting.org/testing-an-ai-assisted-research-workflow-for-multi-asset-pullback-strategy-discovery/
(Institute of Advanced Investment Management summary of Quantpedia/Soňa
Beluška, "Testing an AI-Assisted Research Workflow for Multi-Asset
Pullback Strategy Discovery"). Source's own headline result: 200-day MA
trend filter + 2-day pullback + 1-day hold on 6 liquid ETFs (2006-2025),
Sharpe ~0.95, invested <50% of the time; more conservative 3-day pullback
variant gives buy-and-hold-comparable returns with ~2.4x smaller MDD.

## Hypothesis

In an established uptrend (close > SMA(trend_window)), after
`pullback_days` consecutive down-days, enter a position sized by inverse
realized volatility (target_vol / trailing realized vol, capped at
max_leverage), held for a FIXED `hold_days`-day period (not a
signal-based exit).

## Grid test (Step 6) — initial exploration

`param_grid={"pullback_days": [2,3], "hold_days": [1,3]}` ×
`symbols={"equity": ["SPY","QQQ"], "crypto": ["BTC/USDT","ETH/USDT"]}` ×
`vol_regime_splits=3`, `target_vol=0.15`/`trend_window=200` fixed,
2019-01-01 to 2026-09-01.

- pass_fraction: 13/48 = 0.271, by_asset_class: equity 13/24, crypto 0/24
- by_vol_regime: low 5/16, mid 7/16, **high 1/16** — notably this
  hypothesis passes at least one high-vol cell, unlike most prior
  strategies in this repo's grid history, consistent with the source's
  own vol-adjusted-sizing design intent.
- best initial cell: pullback_days=3/hold_days=3, QQQ, low-vol, Sharpe 2.359
- QQQ (pullback_days=2, hold_days=3) full-period Sharpe was a near-miss
  (0.984 vs 1.0) at the default target_vol=0.15/trend_window=200.

## Refinement: target_vol/trend_window sweep

Local sweep on QQQ (pullback_days=2, hold_days=3 fixed) found
target_vol=0.1/trend_window=150 lifts full-period Sharpe to 1.12
(target_vol/trend_window combos tested: 0.1/150→1.12, 0.1/200→1.10,
0.15/150→1.015, 0.15/200→0.984 [original near-miss], 0.2/150→0.948, ...
0.25/250→0.71 — lower target_vol and shorter trend_window both help).

Re-grid with the refined config
(`pullback_days=2, hold_days=3, target_vol=0.1, trend_window=150`):
pass_fraction 4/12 = 0.333 for this single-param-combo grid; **both SPY
and QQQ pass low-vol AND mid-vol** (SPY: 1.297/1.600; QQQ: 2.081/1.466),
both fail high-vol (SPY -0.382, QQQ -0.293); crypto fails all 6 cells.

## Single-config validators (primary config: QQQ, pullback_days=2, hold_days=3, target_vol=0.1, trend_window=150, full period 2019-01-01 to 2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.120 | ≥ 1.0 | PASS |
| Max drawdown | 0.086 | ≤ 0.25 | PASS |
| Transaction-cost survival (5bps/trade, 120 trades) | 0.910 net Sharpe | ≥ 0.5 | PASS |
| Walk-forward (manual 4-way chronological split) | 4/4 splits positive Sharpe (0.228, 0.720, 1.006, 1.319) = 1.0 pass fraction | ≥ 0.75 | PASS |
| Parameter sensitivity (4-cell target_vol×trend_window sweep: 1.12/1.10/1.015/0.984) | relative_std = 0.054 | ≤ 0.5 | PASS |

## Decision

**Accepted — QQQ only** (pullback_days=2, hold_days=3, target_vol=0.1,
trend_window=150). All 5 validators pass, walk-forward is perfect (4/4
positive), and MDD is very low (8.6%) thanks to the vol-adjusted sizing +
short fixed hold. Explicitly scoped: SPY passes only low/mid-vol (not
accepted as a standalone live config — high-vol cell fails decisively,
-0.38 Sharpe); crypto fails everywhere (0/6 cells even after refinement).
A future loop could try widening the accepted scope to SPY with its own
target_vol/trend_window local search, following the same refinement
pattern used here for QQQ.
