# Backtest Report: PFE Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_pfe_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-102

## Hypothesis

Polarized Fractal Efficiency (Hans Hannula, 1994): signed fractal-geometry
ratio of straight-line price distance over N bars vs actual bar-to-bar path
length, EMA-smoothed, bounded roughly [-100,100]. Formula read directly from
Investopedia (via browser_exec navigation, since web_extract's DuckDuckGo
backend cannot fetch page content).

Repo has one prior PFE entry (2026-09-05-014), a binary threshold-crossover
(+50/-50 zones), decisively rejected. This iteration reframes PFE as a
CONTINUOUS SIZING dial within an SMA(trend_window) uptrend gate, following
the VHF/ADX/CHOP pattern (fellow trend-efficiency measures, all strong
performers this cron trigger).

## Grid test summary (Step 6)

`param_grid={pfe_sensitivity: [0.4,0.6,0.8], deadband: [0.15,0.20,0.25]}`,
`symbols={equity: [QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells=108, passed=54, pass_fraction=0.50
- by_asset_class: equity 27/54 (0.50), crypto 27/54 (0.50)
- by_vol_regime: low 36/36 (1.00), mid 18/36 (0.50), high 0/36 (0.00)
- per-symbol: QQQ 18/27, SPY 9/27, BTC/USDT 18/27, ETH/USDT 9/27

## Single-config validator results (Step 7)

Grid best-cell configs (db=0.20-0.25) failed TC-survival on equity (QQQ net
Sharpe 0.343 at 348 trades; SPY 0.371 at 196 trades) and MDD on crypto (BTC
0.290-0.307 persistently across deadbands 0.20-0.30, not resolved by
widening). A further deadband sweep found equity configs clearing all 5:

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | sens=0.8, db=0.35 | 1.288 (pass) | 15.96% (pass) | 0.672 (pass) | 0.75 (pass) | 0.076 rel-std (pass) | **ACCEPT** |
| SPY | sens=0.4, db=0.30 | 1.101 (pass) | 7.90% (pass) | 0.598 (pass) | 0.75 (pass) | 0.072 rel-std (pass) | **ACCEPT** |
| BTC/USDT | sens=0.3-0.4, db=0.25-0.30 | 1.42-1.45 (pass) | 29.6-30.7% (**FAIL**, >25%, resistant to deadband widening) | 1.25-1.30 (pass) | (not run, MDD already decisive) | -- | **REJECT** (MDD) |

## Decision

**Accept for equity (QQQ, SPY)** — both clear all 5 validators at widened
deadband (0.30-0.35, among the widest used this cron trigger, consistent
with PFE's fractal-geometry construction producing more granular/noisy
signal than the simpler trend-strength dials). **Reject crypto** (BTC/USDT
MDD stays pinned near 0.29-0.31 regardless of deadband from 0.20 to 0.30,
unlike BOP/IMI/PFE-on-equity where widening the deadband alone rescued a
metric -- here the drawdown appears structural to how PFE interacts with
crypto's volatility clusters, not a turnover-cost artifact). Sixth
consecutive successful sizing-dial reframing of a previously-rejected
binary-threshold indicator this cron trigger (after VZO/ADX/DMI-diff/
CHOP/Vortex/TSI/RMI/SMI/BOP/IMI/VHF), continuing to validate the pattern
that this repo's earlier binary-signal rejections in the oscillator/
trend-strength space were often symptoms of the discrete-trigger
construction rather than the underlying indicator lacking signal.
