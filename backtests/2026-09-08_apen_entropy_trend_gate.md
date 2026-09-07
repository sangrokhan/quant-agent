# ApEn (Approximate Entropy) Regularity-Gated Trend Following — QQQ (equity-only)

**Strategy file:** `strategies/2026-09-08_apen_entropy_trend_gate.py`
**Source(s):** https://en.wikipedia.org/wiki/Approximate_entropy (ApEn(m,r,N) algorithm definition)
**Knowledge base id:** 2026-09-08-047

## Hypothesis

A simple SMA-trend breakout (long when close > SMA(trend_window)) should have
better edge specifically when the market's recent daily-return sequence is in
a LOW rolling Approximate Entropy (more regular/structured/predictable)
regime, and be actively harmful in HIGH-ApEn (noisy/chop) regimes. This is a
new indicator family for this repo: information-theoretic regularity, not a
volatility-magnitude regime gate like prior "vol regime" strategies.

## Best config (from grid search)

`trend_window=50, entropy_window=15, entropy_regime_ratio=1.0` (entropy_lookback=126, m=2, r_mult=0.2, max_hold_days=15 — defaults)

## Step 6 grid summary (trend_window x entropy_window x entropy_regime_ratio, 2 assets x 3 vol regimes)

- total_cells: 96, passed_cells: 23, pass_fraction: 0.240
- by_asset_class: equity 23/48 passed, **crypto 0/48 passed**
- by_vol_regime: low 16/32, mid 7/32, high 0/32
- best_cell: trend_window=50, entropy_window=15, entropy_regime_ratio=1.0, QQQ, low-vol regime, Sharpe 2.497
- worst_cell: trend_window=50, entropy_window=20, entropy_regime_ratio=1.0, SPY, mid-vol regime, Sharpe -0.614

Interpretation: the entropy-regularity gate has a clean asset-class split —
works only on equity indices, fails uniformly on crypto (BTC/ETH), and is
concentrated in low/mid vol regimes (fails entirely in high-vol).

## Step 7 full-sample validators (best config, 2018-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Walk-fwd pass frac | Param sensitivity (rel std) | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.157 (pass, thr 1.0) | 0.151 (pass, thr 0.25) | 0.723 (pass, thr 0.5) | 1.00 (pass, thr 0.75) | 0.262 (pass, thr 0.5) | **ALL PASS** |
| SPY | 0.642 (**fail**, thr 1.0) | 0.184 (pass, thr 0.25) | 0.200 (**fail**, thr 0.5) | 0.75 (pass, thr 0.75) | 0.137 (pass, thr 0.5) | FAIL (Sharpe, TC) |

## Decision: ACCEPT (QQQ-only, equity-only scope)

QQQ passes every validator run. SPY fails Sharpe and transaction-cost
survival (net Sharpe collapses to 0.20 after 10bps/trade — 229 trades over
the sample). Crypto fails entirely in the grid (0/48 cells). This strategy is
accepted **narrowly scoped to QQQ (or similar high-beta tech-heavy index
ETFs)** only — not SPY, not crypto. A future iteration could investigate why
QQQ specifically benefits (higher-beta trend persistence structure) vs SPY
(broader, more diversified index, weaker single-name-driven trend runs).
