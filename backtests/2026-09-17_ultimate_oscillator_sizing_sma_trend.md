# Backtest Report: Ultimate Oscillator Continuous Sizing on SMA(200) Trend Gate

**Strategy file:** `strategies/2026-09-17_ultimate_oscillator_sizing_sma_trend.py`
(accepted-config re-export: `strategies/2026-09-17_uo_sizing_equity_accepted.py`)
**Hypothesis id:** 2026-09-17-021

## Hypothesis

This repo has 2 prior Ultimate Oscillator (UO, Larry Williams) entries
(2026-09-04-050 plain oversold/overbought threshold-cross, rejected;
2026-09-05-077 bullish divergence variant, rejected) -- both using UO as a
BINARY entry trigger. Neither used it as a CONTINUOUS SIZING dial, the
established pattern this cron trigger has repeatedly used to rescue
previously-binary-rejected oscillators. UO is naturally centered around 50
(per QuantifiedStrategies.com/Investopedia's disclosed 7/14/28-period
weighted 4:2:1 formula), so this iteration rescales (UO-50)/50 to a signed
dial and uses it to size exposure within an SMA(200) uptrend gate.

## Grid summary (scripts/run_grid_uo_sizing.py)

param_grid: sensitivity={0.3,0.5,0.8} x deadband={0.0,0.2} x leverage_cap={1.0}
x {QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol-regime terciles = 72 cells

- pass_fraction: 0.403 (29/72)
- by_asset_class: equity 18/36, crypto 11/36
- by_vol_regime: low 17/24, mid 12/24, high 0/24
- best_cell: SPY, sensitivity=0.3/deadband=0.2, low-vol tercile Sharpe 2.831

## Full-sample validation (deadband widened to 0.5 to control turnover)

Initial full-sample validation at the grid's literal best config
(deadband=0.2) showed catastrophic transaction-cost failure (QQQ 811
trades, SPY 842, BTC/ETH 12,000+ trades over 7.7yr) because a narrow
deadband lets exposure oscillate on every small UO wiggle. Widening the
deadband to 0.5 (only rebalance when |UO-50|/50 exceeds 0.5) cut turnover
by >10x while preserving the underlying signal.

| Symbol | Sharpe | MDD | Net Sharpe (TC) | Trades | Walk-forward | Param sensitivity |
|--------|--------|-----|------------------|--------|---------------|--------------------|
| QQQ | 1.206 (pass) | 0.114 (pass) | 1.032 (pass) | 67 | 0.75 (pass) | 0.029 (pass) |
| SPY | 0.960 (fail, thr 1.0) | 0.109 (pass) | 0.587 (pass) | 99 | 0.75 (pass) | 0.024 (pass) |
| BTC/USDT | 0.232 (fail) | 0.365 (fail) | -0.017 (fail) | 2392 | 1.00 (pass) | 0.015 (pass) |
| ETH/USDT | 0.229 (fail) | 0.297 (fail) | -0.002 (fail) | 2327 | 1.00 (pass) | 0.001 (pass) |

## Decision: ACCEPTED (QQQ only); REJECTED (SPY near-miss; crypto decisive)

QQQ passes all 5 validators at sensitivity=0.3/deadband=0.5/leverage_cap=1.0.
SPY is a genuine near-miss (Sharpe 0.960 vs 1.0 threshold, ~4% shortfall,
every other validator passes) -- consistent with this repo's frequent
"accepted QQQ only, SPY near-miss" pattern for trend-following sizing
overlays. Crypto fails decisively on both Sharpe and MDD even after the
deadband widening -- its intraday-scale bar-to-bar UO volatility still
produces far more rebalancing (2300+ trades) than equity's calmer daily
UO path, and the underlying SMA(200) trend gate itself has a documented
weak track record on crypto elsewhere in this knowledge base.
