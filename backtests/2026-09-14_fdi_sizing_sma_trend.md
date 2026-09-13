# Backtest Report: Fractal Dimension Index (FDI) Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_fdi_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-109

## Hypothesis

Fractal Dimension Index (Benoit Mandelbrot): rolling-window fractal
self-similarity measure of the price path, natively bounded [1.0, 2.0] --
near 1.0 = straight-line directional trend, near 2.0 = maximally
noisy/ranging. Confirmed via Google SERP + quantifiedstrategies.com +
prorealcode.com (browser_exec fallback after `web_search` failed 3
consecutive times this iteration with a DDGSException connection error to
search.yahoo.com) -- these sources confirm the [1,2] range and 1.5/1.3
thresholds, but the exact box-counting math is paywalled/proprietary, so
this iteration reuses the standard two-segment Ehlers/Mandelbrot
approximation already implemented in this repo's prior FDI entry
(2026-09-08-015, a binary trend-strength REGIME GATE, rejected).

This iteration reframes FDI as a CONTINUOUS SIZING dial, rescaling to
[-1,1] via -(FDI-1.5)/0.5 (natively bounded, no z-score/tanh needed),
following the pure-trend-efficiency family pattern (VHF/CHOP/ADX) that has
repeatedly generalized to BOTH equity and crypto this cron trigger, unlike
the momentum/volume-flow family (EFI/EMV/STC/Qstick) which failed crypto 4
consecutive times.

## Grid test summary (Step 6)

`param_grid={trend_window:[40,60], fdi_sensitivity:[0.5,0.6,0.7], deadband:[0.1,0.15,0.2]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2018-01-01 to 2026-09-01.

- total_cells=216, passed=54, pass_fraction=0.25
- by_asset_class: equity 54/108 (0.50), crypto 0/108 (0.00) -- crypto fails
  every cell (unlike VHF/PFE/RWI/CHOP family, FDI did NOT generalize to
  crypto here despite being natively bounded)
- by_vol_regime: low 36/72 (0.50), mid 18/72 (0.25), high 0/72 (0.00)
- best_cell: QQQ, trend_window=60/sens=0.5/db=0.15, low-vol regime, Sharpe
  2.64

## Single-config validator results (Step 7)

Grid's nominal best cell narrowly missed full-sample Sharpe (0.927). A
broader QQQ sweep (trend_window x {40,60,80}, deadband x {0.1..0.3},
sensitivity x {0.4..0.7}) found a passing config; a 25-combo SPY sweep
(deadband 0.25-0.4, sensitivity 0.4-0.7) never cleared 0.84 Sharpe:

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=60, sens=0.5, db=0.3 | 1.029 (pass) | 15.1% (pass) | 0.850 (pass) | 1.00 (pass) | 0.031 rel-std (pass) | **ACCEPT** |
| SPY | trend_window=60, sens=0.45, db=0.35 (best of 25-combo sweep) | 0.836 (**FAIL**) | 13.1% (pass) | 0.643 (pass) | 1.00 (pass) | 0.088 rel-std (pass, but noticeably higher than QQQ) | **REJECT** (Sharpe, clear miss) |
| BTC/USDT | trend_window=60, sens=0.5, db=0.15 | 0.204 (**FAIL**) | 31.5% (**FAIL**) | -0.040 (**FAIL**) | 1.00 (pass) | 0.028 rel-std (pass) | **REJECT** |

## Decision

**Accept for QQQ (equity) only.** **Reject SPY** — best Sharpe found across
a 25-combo deadband/sensitivity sweep was 0.836, a clear (not near-miss)
shortfall unlike Qstick's 0.991 near-miss last iteration. **Reject
BTC/USDT** — MDD fails at 31.5% (moderately over the 25% threshold, less
severe than EMV/STC's ~40-58% crypto MDD blowouts, but still a fail).
Notably, despite FDI being natively bounded [1,2] like VHF/CHOP (the family
that has repeatedly cleared crypto this trigger), FDI itself does NOT
generalize to crypto here -- suggesting "natively bounded" alone isn't
sufficient; the specific trend-efficiency construction matters (VHF/CHOP
use direct range-vs-path-length ratios, while FDI's box-counting
log-transform behaves differently under crypto's fatter-tailed, higher
day-to-day volatility). This nuance is worth flagging for a future
iteration revisiting the "which trend-efficiency measures generalize to
crypto" question with a wider indicator sample.
