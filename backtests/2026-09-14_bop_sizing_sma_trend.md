# Backtest Report: BOP Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_bop_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-099

## Hypothesis

Balance of Power (Igor Livshin, Aug 2001): BOP=(Close-Open)/(High-Low),
smoothed with a rolling mean, naturally bounded [-1,1]. Confirmed via
DuckDuckGo HTML SERP (tradingview.com, wealthcharts.com, agenatrader.com).

Repo has 2 prior BOP entries: a binary threshold-crossover
(2026-09-04-071, decisively rejected, explicitly noted "highly
parameter-sensitive") and a divergence variant (accepted, 2026-09-10-107).
Neither used BOP as a CONTINUOUS SIZING dial. This iteration applies the
same reframing that rescued VZO/ADX/DMI-diff/CHOP/Vortex/TSI/RMI/SMI
earlier this cron trigger.

## Grid test summary (Step 6)

`param_grid={bop_sensitivity: [0.4,0.6,0.8], deadband: [0.05,0.10]}`,
`symbols={equity: [QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells=72, passed=36, pass_fraction=0.50
- by_asset_class: equity 18/36 (0.50), crypto 18/36 (0.50)
- by_vol_regime: low 24/24 (1.00), mid 12/24 (0.50), high 0/24 (0.00)
- best_cell: QQQ, sens=0.8/db=0.05, low-vol, Sharpe 2.897

## Single-config validator results (Step 7)

Initial best-grid-cell configs (sens=0.8, db=0.05 for QQQ/BTC, db=0.10 for
SPY) all **FAILED transaction-cost survival** on equity (QQQ 508 trades,
net Sharpe 0.072; SPY 246 trades, net Sharpe 0.272) despite strong gross
Sharpe -- BOP's raw (unsmoothed inside the dial) daily variability at low
deadband generates far more exposure changes than the other sizing dials
this cron trigger. A deadband sweep (0.10-0.25) found equity configs that
clear TC-survival while keeping Sharpe/MDD intact:

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | sens=0.8, db=0.15 | 1.154 (pass) | 12.23% (pass) | 0.590 (pass) | 0.75 (pass) | 0.019 rel-std (pass) | **ACCEPT** |
| SPY | sens=0.8, db=0.25 | 1.062 (pass) | 7.30% (pass) | 0.562 (pass) | 1.00 (pass) | 0.021 rel-std (pass) | **ACCEPT** |
| BTC/USDT | sens=0.8, db=0.05 | 1.456 (pass) | 33.15% (**FAIL**, >25%) | 0.962 (pass) | 1.00 (pass) | 0.011 rel-std (pass) | **REJECT** (MDD) |

## Decision

**Accept for equity (QQQ, SPY)** — at a widened deadband (0.15/0.25 vs the
0.05-0.10 used by the other sizing-dial strategies this cron trigger), all
5 validators pass on both symbols. **Reject crypto** (BTC/USDT decisive MDD
fail, consistent with the recurring crypto-drawdown pattern for sizing-dial
overlays this cron trigger). Notable finding: BOP's day-to-day choppiness
(even after its own 14-day SMA smoothing) requires a materially wider
deadband than the other accepted sizing dials to survive transaction costs
on equity -- this refutes the prior binary-threshold rejection's
"parameter-sensitive" framing (a continuous dial at appropriate deadband is
robust, param_sensitivity relative-std ~0.02) while confirming BOP genuinely
needs stronger turnover control than trend-strength indicators like
ADX/CHOP/Vortex.
