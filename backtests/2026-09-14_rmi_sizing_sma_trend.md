# Backtest Report: RMI Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_rmi_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-097

## Hypothesis

Relative Momentum Index (Roger Altman, 1993): RSI's Wilder-smoothing
construction applied to an N-bar momentum step instead of a 1-bar diff,
bounded [0,100]. Confirmed via DuckDuckGo HTML SERP (everycalculators.com,
luxalgo.com, onetradejournal.com, quantstrategy.io).

Repo has one prior RMI entry (2026-09-05-013), a binary oversold-threshold
mean-reversion trigger, rejected for insufficient trades (only 5). This
iteration reframes RMI as a CONTINUOUS SIZING dial (rescaled around its
50-midpoint) within an SMA(trend_window) uptrend gate, following the pattern
that rescued VZO/ADX/DMI-diff/CHOP/Vortex/TSI earlier this cron trigger.

## Grid test summary (Step 6)

`param_grid={rmi_sensitivity: [0.4,0.6,0.8], deadband: [0.05,0.10]}`,
`symbols={equity: [QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells=72, passed=27, pass_fraction=0.375
- by_asset_class: equity 18/36 (0.50), crypto 9/36 (0.25)
- by_vol_regime: low 20/24 (0.83), mid 7/24 (0.29), high 0/24 (0.00)
- per-symbol: QQQ 12/18 (best sharpe 2.75 @ sens=0.8,db=0.1), SPY 6/18 (best
  sharpe 2.49 @ sens=0.4,db=0.1), BTC/USDT 7/18 (best sharpe 1.74 @
  sens=0.4,db=0.05), ETH/USDT 2/18 (best sharpe 2.49 @ sens=0.8,db=0.05)

## Single-config validator results (Step 7)

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | sens=0.8, db=0.1 | 1.195 (pass) | 16.45% (pass) | 0.526 (pass) | 0.75 (pass) | 0.027 rel-std (pass) | **ACCEPT** |
| SPY | sens=0.4, db=0.1 | 0.976 (**FAIL**, <1.0) | 9.12% (pass) | 0.294 (**FAIL**, <0.5) | 0.75 (pass) | 0.016 rel-std (pass) | **REJECT** (Sharpe, TC-survival) |
| BTC/USDT | sens=0.4, db=0.05 | 1.454 (pass) | 34.70% (**FAIL**, >25%) | 1.060 (pass) | 1.00 (pass) | 0.008 rel-std (pass) | **REJECT** (MDD) |

## Decision

**Accept for QQQ only** — all 5 validators pass. **Reject SPY** (fails
Sharpe and transaction-cost survival at its best-grid config despite passing
in the grid's own aggregate Sharpe-only pass criteria — the 339/243-trade
counts drove real cost drag the grid test's simpler check didn't fully
capture). **Reject crypto** (BTC/USDT decisive MDD fail at 34.7% vs 25%
threshold, worse than the sizing-dial family's typical crypto MDD misses
this cron trigger). This narrows RMI's earlier open question (whether the
2026-09-05-013 rejection was purely a binary-threshold/low-trade-count
artifact) to: the sizing-dial reframing helps but is QQQ-specific here,
unlike VZO/ADX/DMI-diff/CHOP/Vortex/TSI which all cleared both QQQ and SPY.
