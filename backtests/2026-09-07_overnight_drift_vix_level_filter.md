"""Backtest report: Overnight-drift with elevated-VIX-level filter.

Hypothesis id: 2026-09-07-020 (see knowledge_base/strategies_log.jsonl)
Strategy file: strategies/2026-09-07_overnight_drift_vix_level_filter.py
Outcome: **REJECTED**

## Hypothesis

Per the NY Fed staff report "The Overnight Drift" (Boyarchenko, Larsen,
Whelan) -- read via Google AI-overview + search-result snippets since the
PDF is JS/paywall-blocked to web_extract -- average overnight returns are
higher following days with a greater end-of-day VIX level. This repo
already accepted the unconditional overnight-hold anomaly for QQQ
(2026-09-03-007), so this iteration tests whether gating that same
overnight-only hold to only "VIX elevated vs its own rolling median" days
improves risk-adjusted performance vs the unconditional version.

## Step 6 grid summary (vix_lookback in [40,60,90] x vix_regime_ratio in
[1.05,1.15,1.3], symbols QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3)

- total_cells: 108, passed_cells: 20, **pass_fraction: 0.185**
- by_asset_class: equity 20/54 (0.370), crypto 0/54 (0.0 -- expected
  falsification, no VIX index / no discrete session boundary for crypto)
- by_vol_regime: low 13/36 (0.361), mid 7/36 (0.194), high 0/36 (0.0)
- best_cell: QQQ, vix_lookback=90, vix_regime_ratio=1.15, low-vol regime,
  Sharpe 1.848
- worst_cell: SPY, vix_lookback=40, vix_regime_ratio=1.15, high-vol regime,
  Sharpe -0.679
- Best full-sample-equity param combo by per-cell pass count:
  vix_lookback=90, vix_regime_ratio=1.05 (3/6 QQQ+SPY cells passed)

## Step 7 single-config validation (vix_lookback=90, vix_regime_ratio=1.05,
full 2019-2026 sample, QQQ & SPY)

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.574 (FAIL) | 0.364 (FAIL) | >= 1.0 |
| Max drawdown | 0.271 (FAIL) | 0.292 (FAIL) | <= 0.25 |
| Tx-cost survival (5bps, 87 trades) | 0.511 (PASS) | 0.296 (FAIL) | >= 0.5 net Sharpe |
| Parameter sensitivity (9-combo QQQ sweep) | relative_std 0.515 (FAIL) | -- | <= 0.5 |
| Walk-forward | not run -- pre-existing `vbt.utils.splitting` AttributeError bug in installed vectorbt, same known issue noted in prior reports this cron trigger | | |

## Decision

**Rejected.** Full-sample Sharpe, max drawdown, and parameter sensitivity
all fail for both QQQ and SPY despite a respectable grid pass_fraction
concentrated in the low-vol-regime tercile (13/36, best single cell Sharpe
1.848 for QQQ). The VIX-level-elevated gate does not durably beat the
already-accepted unconditional overnight-hold (2026-09-03-007): elevated
VIX days appear correlated with the HIGH realized-vol regime where this
grid's pass rate is 0/36, i.e. the filter tends to select exactly the
regime where overnight moves are largest in both directions (higher
variance, not necessarily higher risk-adjusted drift), pulling down
full-sample Sharpe and blowing through the MDD threshold. Crypto rejected
decisively as expected (no VIX, own-vol proxy fallback produced 0/54
grid cells).

Source: https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf
(content read via Google search AI-overview synthesis, browser_exec fallback
since web_search's DuckDuckGo backend errored on this query and web_extract
would face a PDF/paywall block).
"""
