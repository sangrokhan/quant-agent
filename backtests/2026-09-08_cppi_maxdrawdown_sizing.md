# Backtest Report: CPPI Max-Drawdown Extension Sizing Overlay (2026-09-08)

**Status: REJECTED (QQQ is a flagged near-miss)** — strategy file kept in
`strategies/` as a record.

## Hypothesis

Per Quantpedia "Introduction to CPPI – Constant Proportion Portfolio
Insurance" (https://quantpedia.com/introduction-to-cppi-constant-proportion-portfolio-insurance/),
CPPI dynamically scales risky-asset exposure via `multiplier * cushion`,
where `cushion = portfolio_value - floor`. The article's own "Maximum
Drawdown extension" sets the floor as `max_drawdown_floor_pct * running_max`
of the portfolio's own value — directly targeting a max-drawdown ceiling.

This is a direct follow-up to this cron trigger's own HMM regime-filter
near-miss (2026-09-08-173), which failed decisively on max_drawdown (0.386
QQQ) despite passing every other validator — CPPI's floor mechanism targets
exactly that failure mode via continuous sizing instead of a binary gate.

## Single-config validator results (best grid config: `multiplier=2.0`, `max_drawdown_floor_pct=0.85`)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Walk-forward | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| SPY | 0.822 ❌ | 0.057 ✅ | 0.357 ❌ | 0.75 ✅ | 0.032 ✅ | 78 |
| QQQ | **1.084 ✅** | **0.060 ✅** | 0.415 ❌ | **1.0 ✅** | **0.030 ✅** | 146 |

## Grid test summary

`param_grid={multiplier:[2.0,3.0,4.0], max_drawdown_floor_pct:[0.85,0.9]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`
(2018-01-01 to 2026-09-01), 72 total cells.

- **Overall pass_fraction: 0.25** (18/72 cells)
- By asset class: equity 18/36 passed, **crypto 0/36 passed** (decisive reject)
- By vol regime: low 12/24, mid 6/24, high 0/24
- Best cell: SPY, low-vol, `multiplier=2.0/floor=0.85`, Sharpe 2.349
- Worst cell: QQQ, high-vol, `multiplier=4.0/floor=0.9`, Sharpe -0.337

## Decision

**Reject**, but **QQQ is a strong near-miss**: Sharpe (1.084), max drawdown
(0.060 — a dramatic improvement over the 0.386 that sank the HMM regime
filter this same cron trigger, confirming the CPPI drawdown-floor mechanism
works exactly as designed), walk-forward (1.0), and parameter sensitivity
(0.030) all pass comfortably. The ONLY failing validator is transaction-cost
survival (net Sharpe 0.415 < 0.5 threshold), driven by high rebalancing
frequency (146 weight changes >1% over 8.5yr from continuous CPPI resizing).

SPY fails Sharpe (0.822) and txcost outright, though MDD and walk-forward
still pass. Crypto rejected decisively (0/36 cells).

**Follow-up flagged for a future iteration:** add a minimum rebalance-change
threshold (e.g. only re-trade when weight moves >5-10% rather than any >1%
change) or a fixed weekly/monthly rebalance cadence to cut QQQ's trade count
substantially while preserving the drawdown-control edge, before this idea
is abandoned.
