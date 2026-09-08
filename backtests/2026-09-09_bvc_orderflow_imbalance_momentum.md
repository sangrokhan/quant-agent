# BVC Order-Flow Imbalance Momentum — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_bvc_orderflow_imbalance_momentum.py`
**Source:** https://quantmedia.io/learn/what-is-vpin (Bulk Volume Classification / VPIN
explainer, read this iteration via browser fallback after `web_search` failed
with a DuckDuckGo backend error).

## Hypothesis

Bulk Volume Classification (BVC) infers buy- vs sell-initiated daily volume
from the standardized close-to-close return via a normal CDF
(`buy_frac = Phi(return/sigma)`), without needing tick data. This repo only
has daily OHLCV (no order-flow/tick feed), so literal VPIN (equal-volume
buckets + `|Vb-Vs|` averaging) is infeasible, but the BVC buy/sell-fraction
primitive works on daily bars. This strategy computes a trailing,
volume-weighted, *signed* BVC imbalance (`2*buy_frac - 1`, volume-weighted
over a rolling window) and goes long while it stays above an entry
threshold (hysteresis exit below a lower threshold). Distinct from the
already-rejected OBV-divergence construction (2026-09-08-019), which used
OBV's cumulative running total and price/OBV divergence rather than a
continuous BVC-signed order-flow momentum signal.

## Grid test (Step 6)

`imbalance_window ∈ {10, 20}` x `entry_threshold ∈ {0.05, 0.10, 0.15}` x
{QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles = 72 cells.

- **pass_fraction: 0.278** (20/72)
- by_asset_class: equity 20/36 passed, **crypto 0/36 (decisive fail)**
- by_vol_regime: low 12/24, mid 7/24, high 1/24
- best_cell: QQQ, low-vol, `imbalance_window=10, entry_threshold=0.15`, Sharpe 2.46
- worst_cell: QQQ, high-vol, `imbalance_window=20, entry_threshold=0.15`, Sharpe -0.75

## Single-config validation (best config: `imbalance_window=10, entry_threshold=0.15`)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.953 (FAIL) | 0.791 (FAIL) | ≥ 1.0 |
| Max drawdown | 0.183 (PASS) | 0.172 (PASS) | ≤ 0.25 |
| Net Sharpe after costs (10bps/trade) | 0.848 (PASS) | 0.639 (PASS) | ≥ 0.5 |
| Walk-forward pass fraction (4 slices, manual fallback) | 1.0 (PASS) | 0.75 (PASS) | ≥ 0.75 |
| Parameter sensitivity (relative std, 6-cell grid) | 0.087 (PASS) | 0.276 (PASS) | ≤ 0.5 |

Trade counts: QQQ 64, SPY 70 (2019-01-01 to 2026-09-01).

## Decision: REJECTED

Full-sample Sharpe falls short of the 1.0 threshold on both equity symbols
(QQQ 0.95 is a near-miss, SPY 0.79 is a clearer shortfall), despite the
strategy otherwise passing every other validator (MDD, transaction-cost
survival, walk-forward, parameter sensitivity) and having the second-best
grid pass_fraction (0.278) of any strategy logged in this repo. The grid's
best cells cluster in the low-vol tercile at the tightest entry threshold
(0.15) — the full-sample Sharpe drag comes from weaker performance in
mid/high-vol regimes (only 7/24 and 1/24 grid cells pass respectively).
Crypto (BTC/USDT, ETH/USDT) failed decisively across all 36 cells — the BVC
signal, tuned on daily-close/volume, does not transfer to crypto's
different volume/return microstructure.

**Note for future iterations:** this is a genuine near-miss, not a decisive
rejection. A vol-regime-gated version (e.g. only take BVC-imbalance signals
in the low/mid-vol terciles, flat in high-vol) could plausibly clear
Sharpe ≥ 1.0 given the regime breakdown above — worth revisiting with an
explicit vol-regime gate layered on top of this same BVC primitive.
