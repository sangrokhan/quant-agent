# Adaptive Weekly Momentum Exit ("One Percent a Week" variant) — Backtest Report

**Date:** 2026-09-12
**Strategy file:** `strategies/2026-09-12_tqqq_adaptive_weekly_momentum_exit.py`
**Source:** TASC June 2026 Traders' Tips (Dion Kurczek), via
https://www.tradingview.com/script/CSGmHoik-TASC-2026-06-One-Percent-A-Week-Adaptive/

## Hypothesis

Enter long at Monday's open; fixed 1.5% stop; initial 7% take-profit target
that adapts up (x1.011) or down (to 2.5%) based on Monday's close performance;
close early if Tuesday shows loss of Monday's momentum (Monday return > 2%
but Tuesday return < 3%); otherwise let stop/target run through the week and
force-close at week end. Adapted to daily OHLC bars (intrabar stop/target
proxied via daily high/low touches).

## Best config (from grid search)

`stop_pct=0.02, initial_target_pct=0.05` (other params at source defaults:
`momentum_gate_pct=0.003, target_scale_up=1.011, reduced_target_pct=0.025,
monday_thresh=0.02, tuesday_thresh=0.03`)

## Single-config validator results (2018-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward pass | Param sensitivity (rel. std) |
|---|---|---|---|---|---|
| QQQ | 1.172 (pass, thr 1.0) | **36.1% (FAIL, thr 25%)** | 0.991 (pass, thr 0.5) | 4/4 (pass) | 0.069 (pass, thr 0.5) |
| SPY | 1.133 (pass, thr 1.0) | 17.6% (pass, thr 25%) | 1.002 (pass, thr 0.5) | 4/4 (pass) | 0.020 (pass, thr 0.5) |

QQQ fails max-drawdown; SPY passes all 5 validators.

## Grid-test summary (2019-01-01 to 2026-09-01)

Grid: `stop_pct in {0.01, 0.015, 0.02} x initial_target_pct in {0.05, 0.07}`,
symbols `{QQQ, SPY} x {BTC/USDT, ETH/USDT}`, vol_regime_splits=3. 72 total
cells (min_sharpe=1.0, max_mdd=0.25 per-cell thresholds).

- Overall pass_fraction: 0.306 (22/72)
- By asset class: equity 22/36 passed; **crypto 0/36 passed (decisive reject)**
- By vol regime: low 12/24, mid 6/24, high 4/24
- Best cell: QQQ, stop_pct=0.02/initial_target_pct=0.05, low-vol, Sharpe 2.48
- Worst cell: ETH/USDT, stop_pct=0.02/initial_target_pct=0.05, mid-vol, Sharpe -0.11

## Decision: ACCEPT (SPY only) / REJECT (QQQ, crypto)

SPY passes all 5 validators at the best grid config. QQQ fails max-drawdown
(36.1% vs 25% threshold) at full-sample despite passing Sharpe/TC/walk-forward
/param-sensitivity -- QQQ's higher volatility interacts badly with this
strategy's wide 7%-initial-target weekly hold. Crypto (BTC/ETH) is decisively
rejected across the whole grid (0/36). Scope this strategy to SPY only.
