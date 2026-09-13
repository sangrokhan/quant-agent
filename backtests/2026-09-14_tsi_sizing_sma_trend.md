# Backtest Report: TSI Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_tsi_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-096

## Hypothesis

True Strength Index (William Blau, 1991): double-smoothed momentum ratio,
`TSI = 100 * EMA(EMA(price_diff, slow), fast) / EMA(EMA(|price_diff|, slow), fast)`,
bounded roughly [-100, 100]. Confirmed via DuckDuckGo HTML search results
(nexusfi.com, trendsandbreakouts.com, TA-Lib/ta-lib GitHub issue #360).

Repo has 7 prior TSI entries, all binary threshold/crossover/signal-line
entry triggers, all rejected. This iteration reframes TSI as a CONTINUOUS
SIZING dial within an SMA(trend_window) uptrend gate (exposure scales with
TSI level rather than triggering discrete entries), following the pattern
that rescued VZO/ADX/DMI-diff/CHOP/Vortex earlier this cron trigger.

## Grid test summary (Step 6)

`param_grid={tsi_sensitivity: [0.4,0.6,0.8], deadband: [0.05,0.10]}`,
`symbols={equity: [QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells=72, passed=36, pass_fraction=0.50
- by_asset_class: equity 18/36 (0.50), crypto 18/36 (0.50) -- unusually even; most
  prior sizing-dial strategies this cron trigger were equity-only
- by_vol_regime: low 24/24 (1.00), mid 12/24 (0.50), high 0/24 (0.00) -- strategy
  works only in low/mid realized-vol regimes, fails outright in high-vol
- per-symbol best cells: QQQ 12/18 (sharpe 2.69 @ sens=0.6,db=0.1), SPY 6/18
  (sharpe 2.62 @ sens=0.4,db=0.1), BTC/USDT 12/18 (sharpe 1.80 @ sens=0.6,db=0.1),
  ETH/USDT 6/18 (sharpe 2.46 @ sens=0.4,db=0.1)
- best_cell: QQQ, sens=0.6/db=0.1, low-vol regime, Sharpe 2.686
- worst_cell: QQQ, sens=0.8/db=0.05, high-vol regime, Sharpe -0.450

## Single-config validator results (Step 7)

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | sens=0.6, db=0.1 | 1.088 (pass) | 14.06% (pass) | 0.589 (pass) | 0.75 (pass) | 0.016 rel-std (pass) | **ACCEPT** |
| SPY | sens=0.4, db=0.1 | 1.085 (pass) | 6.97% (pass) | 0.535 (pass) | 0.75 (pass) | 0.041 rel-std (pass) | **ACCEPT** |
| BTC/USDT | sens=0.6, db=0.1 | 1.469 (pass) | 31.17% (**FAIL**, >25%) | 1.278 (pass) | 1.00 (pass) | 0.008 rel-std (pass) | **REJECT** (MDD) |

## Decision

**Accept for equity (QQQ, SPY)** — all 5 validators pass on both symbols,
strong walk-forward and very low parameter sensitivity. **Reject for
crypto** (BTC/USDT fails max-drawdown threshold decisively despite
otherwise-strong Sharpe/TC/WF/param-sensitivity; ETH/USDT not separately
validated given BTC's decisive MDD fail and the grid's overall crypto
pass_fraction matching equity coincidentally driven by different vol-regime
mix). Consistent with this cron trigger's established pattern: continuous
sizing-dial overlays on the SMA trend gate work well on equity but carry
excess crypto drawdown risk even when Sharpe looks attractive.

Scope note: only the low/mid vol-regime terciles are validated as reliable
(grid shows 0/24 in high-vol cells across all symbols) — a future iteration
could test an explicit high-vol regime gate/exit on top of this construction.
