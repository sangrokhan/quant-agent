# Backtest Report: CPPI Max-Drawdown Sizing — Rebalance-Threshold Refinement (2026-09-08)

**Status: ACCEPTED (QQQ only)** — refines near-miss 2026-09-08-174.

## Hypothesis

Direct refinement of this cron trigger's own near-miss (2026-09-08-174):
the CPPI Max-Drawdown-extension sizing overlay passed every validator on
QQQ except transaction-cost survival, driven by high rebalancing frequency
(146 weight changes >1% over 8.5yr from continuous CPPI resizing). Added a
`rebalance_threshold` no-trade band: only actually re-trade when the freshly
computed CPPI target weight differs from the currently-held weight by more
than the threshold. Swept `rebalance_threshold` in [0.05, 0.1, 0.15, 0.2] on
QQQ:

| rebalance_threshold | trades | Sharpe | MDD | net Sharpe (10bps) |
|---|---|---|---|---|
| 0.05 | 48 | 1.033 | 0.062 | 0.819 |
| **0.1** | **35** | **1.066** | **0.059** | **0.915** |
| 0.15 | 33 | 1.061 | 0.056 | 0.889 |
| 0.2 | 14 | -0.076 | 0.056 | -0.180 (band too wide, misses key rebalances) |

`rebalance_threshold=0.1` selected.

## Single-config validator results (`multiplier=2.0`, `max_drawdown_floor_pct=0.85`, `rebalance_threshold=0.1`)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Walk-forward | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| **QQQ** | **1.066 ✅** | **0.059 ✅** | **0.915 ✅** | **1.0 ✅** | **0.016 ✅** | **35** |
| SPY | 0.813 ❌ | 0.051 ✅ | 0.446 ❌ | 0.75 ✅ | 0.028 ✅ | 53 |

**QQQ passes all 5 validators — ACCEPTED.**

## Grid test summary

`param_grid={multiplier:[2.0,3.0], rebalance_threshold:[0.05,0.1,0.15]}`
(`max_drawdown_floor_pct=0.85` fixed from 2026-09-08-174's best config),
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`
(2018-01-01 to 2026-09-01), 72 total cells.

- Overall pass_fraction: 0.25 (18/72 cells)
- By asset class: equity 18/36 passed, crypto 0/36 passed
- By vol regime: low 12/24, mid 6/24, high 0/24
- Best cell: SPY, low-vol, Sharpe 2.425
- Worst cell: BTC/USDT, high-vol, Sharpe -0.312

## Decision

**Accept for QQQ only** (config: `trend_window=200`, `multiplier=2.0`,
`max_drawdown_floor_pct=0.85`, `rebalance_threshold=0.1`, `leverage_cap=1.0`).
This is the first accepted strategy from this cron trigger's outer loop.
SPY remains a near-miss and is NOT accepted (Sharpe 0.813, net Sharpe 0.446
both below threshold). Crypto rejected decisively across all 36 cells —
scope explicitly limited to QQQ equity only.
