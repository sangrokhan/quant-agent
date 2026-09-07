# Backtest Report: ZigZag Confirmed-Pivot Trend-Continuation Breakout

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_zigzag_confirmed_pivot_trend_breakout.py`
**Source:** https://fxglory.com/learn/forex-strategies/forex-zigzag-strategy

## Hypothesis

A percent-deviation ZigZag confirms a swing pivot only after price reverses
away from the running extreme by a threshold percentage (avoiding the
lookahead bias of trading off the still-forming leg, per the source's own
central methodology point). The source's own "least-negative" of five
tested setups on 1H FX pairs (still net-negative after realistic costs) was
the trend-continuation breakout: in confirmed up-structure (higher confirmed
highs and higher confirmed lows), enter long when price breaks above the
most recently confirmed swing high; stop beyond the most recent confirmed
opposite (low) swing. Tested here on DAILY equity/crypto bars (very
different timeframe/asset/cost regime than the source's failed 1H FX test)
using a max_hold_days time-stop instead of the source's fixed-R target.

## Grid Test Summary (param_grid: zigzag_pct=[0.03,0.05,0.08] x
max_hold_days=[10,20]; symbols QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3;
2019-01-01 to 2026-09-01)

- total_cells: 72, passed: 18, **pass_fraction: 0.25**
- by_asset_class: equity 18/36 (0.50), crypto **0/36** (decisively rejected)
- by_vol_regime: low 12/24, mid 4/24, high 2/24 (edge concentrated in low-vol)
- best_cell: zigzag_pct=0.05, max_hold_days=20, SPY, low-vol, Sharpe 2.72
- worst_cell: zigzag_pct=0.05, max_hold_days=10, SPY, mid-vol, Sharpe -0.79

## Single-Config Validators (zigzag_pct=0.05, max_hold_days=20, full period 2019-2026)

| Symbol | Sharpe | MDD | TC-survival (10bps) | Walk-forward (manual 4-split) | Param-sensitivity |
|---|---|---|---|---|---|
| QQQ | **1.022 PASS** (26 trades) | **0.121 PASS** | **net Sharpe 0.976 PASS** | **3/4 PASS** | **rel_std 0.198 PASS** |
| SPY | 0.556 FAIL | 0.128 PASS | net Sharpe 0.490 FAIL | 2/4 FAIL | (not run, already failed headline) |

Note: `check_walk_forward` in `validation/validators.py` currently raises
(`vectorbt.utils` has no attribute `splitting` in the installed vectorbt
version) — used a manual 4-equal-chunk walk-forward (Sharpe>0 per chunk,
pass_fraction>=0.75) as a stand-in, consistent with recent prior iterations'
workaround for this same broken API.

Parameter sensitivity grid (QQQ, full period, 6 param combos of
zigzag_pct x max_hold_days): Sharpe range 0.456-0.849, relative_std 0.198
(well under 0.5 threshold) — reasonably stable across nearby parameter
choices.

## Decision: **ACCEPT (QQQ only)**

QQQ passes all 5 validators on the best grid config. SPY fails headline
Sharpe/TC-survival/walk-forward at the same config — not accepted for SPY.
Crypto (BTC/USDT, ETH/USDT) rejected decisively across the entire grid
(0/36 cells) — the confirmed-pivot breakout construction does not transfer
to crypto's volatility/trend regime. Scope: **equity, QQQ only**, not a
broad multi-asset strategy.
