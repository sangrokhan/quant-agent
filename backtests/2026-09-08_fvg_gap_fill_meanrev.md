# Backtest Report: FVG Gap-Fill Mean Reversion (daily bars)

**Strategy file:** `strategies/2026-09-08_fvg_gap_fill_meanrev.py`
**Date:** 2026-09-08
**Outcome:** REJECTED

## Hypothesis

Per ICT/"smart money concepts" (source: https://journali.io/strategies/ict-fvg,
which discloses its own backtest: raw FVG fill rate ~78% on ES/NQ, trading
only fills aligned with higher-timeframe bias improves to ~65% WR), a 3-bar
"fair value gap" (bar1 high < bar3 low = bullish imbalance) tends to get
revisited/filled. This repo tests a DAILY-bar analog: detect bullish 3-bar
FVGs, require close above `trend_sma_window`-day SMA (source's own "align
with higher-timeframe bias" rule), enter when price retraces into the fresh
(< `max_gap_age_days` old, not yet closed below gap bottom) gap zone, exit at
gap-top target, an ATR stop below gap bottom, or a time-stop.

Distinct from the repo's other gap-based strategies (2026-09-03-010,
2026-09-08-016), which use the overnight-open-vs-prior-close gap definition,
not the 3-bar ICT/FVG imbalance definition.

## Grid test summary (Step 6)

`trend_sma_window` in [30,50] x `max_gap_age_days` in [5,10] x
`stop_atr_mult` in [1.0,1.5], symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT],
vol_regime_splits=3 (low/mid/high terciles), start=2018-01-01 end=2026-09-01.

- total_cells: 96, passed_cells: 8, **pass_fraction: 0.083**
- by_asset_class: equity 8/48 passed, crypto **0/48** (decisive fail — daily
  crypto bars apparently don't produce the same tradable gap-fill dynamic,
  or gaps are too frequent/noisy at crypto's volatility to filter cleanly)
- by_vol_regime: low 0/32, **mid 8/32**, high 0/32 — edge concentrated
  entirely in the mid-volatility tercile
- All 8 passing cells are SPY, mid-vol-regime only (never QQQ, never
  low/high vol)
- best_cell: `{trend_sma_window:50, max_gap_age_days:5, stop_atr_mult:1.0}`
  SPY mid-vol, Sharpe 1.547, MDD 0.020

## Single-config validators (Step 7): best config = SPY, trend_sma_window=50,
max_gap_age_days=5, stop_atr_mult=1.0, full sample 2018-01-01..2026-09-01

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio (full sample) | ❌ | 0.610 | ≥ 1.0 |
| max_drawdown | ✅ | 0.049 | ≤ 0.25 |
| transaction_cost_survival (10bps/trade, 137 trades) | ❌ | net Sharpe 0.023 | ≥ 0.5 |
| walk_forward (manual 4-equal-slice fallback; `vbt.utils.splitting.RangeSplitter` still broken in this install) | ✅ | 4/4 splits positive Sharpe | ≥ 0.75 pass fraction |
| parameter_sensitivity (4 nearby SPY-mid-vol cells) | ✅ | relative_std 0.102 | ≤ 0.5 |

## Decision: REJECT

The mid-vol-regime slice alone looks attractive (Sharpe 1.55) but this does
not survive to the full-sample Sharpe (0.61, diluted by low/high-vol
regimes where the strategy is flat/losing) nor transaction costs (137
round-trip trades over the sample at 10bps drags net Sharpe to ~0.02,
decisive fail). Crypto is a categorical 0/48 across the whole grid. Net:
the source's own claimed edge (78% fill rate, 65% WR with bias filter) may
be real on intraday ES/NQ bars as the source tested it, but the daily-bar
translation in this repo does not survive cost/regime-robustness checks.
Narrow honest scope: works (grid-passes) only on SPY during mid-volatility
regimes; fails everywhere else and on the full-sample/cost-adjusted checks.
