# Backtest Report: Mark Minervini's Trend Template (7 single-symbol criteria)

**Strategy file:** `strategies/2026-09-12_minervini_trend_template.py`
**Status:** REJECTED (near-miss)

## Hypothesis
Per ChartMill.com's step-by-step guide (fully disclosed, no paywall):
https://www.chartmill.com/documentation/stock-screener/technical-analysis-trading-strategies/496-Mark-Minervini-Trend-Template-A-Step-by-Step-Guide-for-Beginners

Mark Minervini's 8-criteria "Trend Template" for Stage 2 uptrend
identification. This test uses the 7 criteria computable from single-symbol
OHLCV (price>150MA, price>200MA, 150MA rising, 200MA rising, 50MA>150MA,
50MA>200MA, price>=30% above 52wk low, price within 25% of 52wk high) --
the 8th criterion (cross-sectional Relative Strength rank>=70 vs ALL other
stocks in a universe) is feasibility-blocked (same reasoning as
2026-09-11-102: this repo's data/loaders.py is single-symbol OHLCV only).
Long entry when ALL 7 criteria simultaneously true; exit when any breaks or
a max_hold_days time-stop.

Distinct from already-tested VCP (2026-09-06-111, Minervini's specific entry
pattern) -- this targets his broader regime-qualification checklist instead.

## Grid test summary (Step 6)
- Grid: low_pct_above ∈ {0.25,0.30}, high_pct_within ∈ {0.20,0.25},
  slope_lookback ∈ {10,20}; symbols QQQ/SPY (equity), BTC/USDT, ETH/USDT
  (crypto); vol_regime_splits=3.
- Total cells: 96, passed: 24, **pass_fraction = 0.25**
- By asset class: equity 24/48, crypto 0/48 (decisive reject)
- By vol regime: low 16/32, mid 8/32, high 0/32
- Best cell: low_pct_above=0.25, high_pct_within=0.20, slope_lookback=20,
  QQQ, low-vol tercile, Sharpe=2.21
- Worst cell: low_pct_above=0.30, high_pct_within=0.20, slope_lookback=10,
  QQQ, high-vol tercile, Sharpe=-0.31

## Single-config validation (Step 7), best grid config full-sample (2015-2026)
Params: low_pct_above=0.25, high_pct_within=0.20, slope_lookback=20

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | 0.84 **FAIL** (near-miss) | 0.77 **FAIL** (near-miss) |
| Max Drawdown (<=0.25) | 0.202 PASS | 0.104 PASS |
| TC survival (net Sharpe>=0.5, 10bps/trade) | 0.78 PASS (58 trades) | 0.70 PASS (45 trades) |
| Parameter sensitivity (relative_std<=0.5) | 0.105 PASS (18-combo grid, both symbols, low_pct_above∈{0.20,0.25,0.30}×high_pct_within∈{0.15,0.20,0.25}) | (same combined grid) |

Walk-forward not run (same pre-existing `validation/validators.py`
`check_walk_forward` infra bug hit by prior iterations this cron trigger).

## Decision
**Reject** (near-miss, same pattern as this cron trigger's ChartMill CTI
result 2026-09-12-163). Sharpe falls short on both symbols (0.84 QQQ, 0.77
SPY) despite strong MDD/TC/parameter-sensitivity. Crypto decisively rejected
(0/48). This is now the SECOND consecutive "all-criteria regime filter"
near-miss this cron trigger with very low parameter sensitivity
(relative_std ~0.10-0.13) -- a pattern worth flagging for a future
iteration: consider whether a modest volatility-scaled position-sizing
overlay (rather than binary 0/1 exposure) could push these regime-filter
strategies' Sharpe over 1.0 without materially increasing risk.
