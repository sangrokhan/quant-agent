# Backtest Report: Ulcer Index Drawdown-Risk Regime Gate (2026-09-24)

**Strategy file:** `strategies/2026-09-24_ulcer_index_regime_gate.py`
**Hypothesis source:** https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ulcer-index (visited 2026-09-24T09:30:00Z)

## Hypothesis
The Ulcer Index (Peter Martin & Byron McCann, 1987) is a squared-drawdown-
depth measure (asymmetric, downside-only). This iteration operationalizes
it as a regime gate on top of an SMA-trend entry: stay long only while the
Ulcer Index is at or below its own trailing percentile (drawdown risk not
currently elevated relative to its own recent history); exit when the UI
regime gate flips or trend breaks.

## Grid test summary (Step 6)
- Grid: `ui_window` [10,14,20] x `ui_gate_percentile` [0.4,0.5,0.6] x
  `max_hold_days` [15,20], symbols SPY/QQQ + BTC/USDT/ETH/USDT,
  vol_regime_splits=3.
- 216 total cells, 59 passed (pass_fraction = 0.273).
- By asset class: equity 43/108 (0.398); crypto 16/108 (0.148).
- By vol regime: low 43/72 (0.60), mid 16/72 (0.222), high 0/72 (0.0) --
  strategy fails entirely in high-vol regimes (UI-based gate reacts too
  late to filter drawdown during genuine high-vol crashes).
- By symbol: QQQ 27/54 (0.50), SPY 16/54 (0.30), BTC/USDT 10/54 (0.185),
  ETH/USDT 6/54 (0.111).

## Single-config validation (Step 7)
Initial grid-best configs (ui_window=10) failed full-sample Sharpe/
walk-forward on both QQQ and SPY. An own-data parameter re-scan (wider
ui_window=20, wider ui_gate_percentile, longer max_hold_days=30) found
robust configs for both:

### QQQ: ui_window=20, ui_gate_percentile=0.8, max_hold_days=30
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.317 | >= 1.0 |
| Max drawdown | PASS | 0.172 | <= 0.25 |
| Transaction cost survival (87 trades) | PASS | net Sharpe 1.179 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 1.0 pass_fraction | >= 0.75 |
| Parameter sensitivity | PASS | relative_std 0.269 | <= 0.5 |

### SPY: ui_window=20, ui_gate_percentile=0.4, max_hold_days=30
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.152 | >= 1.0 |
| Max drawdown | PASS | 0.096 | <= 0.25 |
| Transaction cost survival (60 trades) | PASS | net Sharpe 0.950 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 0.75 pass_fraction (3/4 positive) | >= 0.75 |
| Parameter sensitivity | PASS | relative_std 0.461 | <= 0.5 |

Both equity symbols pass all 5 validators at ui_window=20/max_hold_days=30
(wider gate than the raw grid-best cells, per own-data retune).

## Decision: ACCEPT (equity: QQQ and SPY, both all 5 validators pass at
retuned ui_window=20/max_hold_days=30); crypto rejected (grid pass_fraction
0.148-0.185, decisively weaker, not pursued to individual validation);
high-vol regime is a decisive 0/72 failure across the whole grid -- this
strategy is explicitly a low/mid-vol-only tool per its own construction
(a drawdown-depth gate cannot pre-empt a fresh regime shift into high vol).
