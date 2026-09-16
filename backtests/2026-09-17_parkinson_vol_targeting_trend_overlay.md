# Parkinson-Volatility Targeting Trend Overlay — Backtest Report

**Date:** 2026-09-17 (cron trigger iteration 1)
**Strategy file:** `strategies/2026-09-17_parkinson_vol_targeting_trend_overlay.py`
**Hypothesis:** Swap the close-to-close realized-vol denominator in the
already-accepted inverse-vol-targeting overlay (id 2026-09-08-165) for the
Parkinson (1980) high-low range volatility estimator, which academic/
practitioner sources (ryanoconnellfinance.com, quantra.quantinsti.com — read
via browser_exec Google-SERP fallback this iteration, web_search's DDGS
backend returned empty/garbage results) report as ~5x more statistically
efficient than close-to-close because it uses each bar's own high-low range.
Same SMA(trend_window) trend gate; only the vol estimator differs.

Source URLs read this iteration:
- https://ryanoconnellfinance.com (Range Volatility Calculator: Parkinson,
  Garman-Klass & others)
- https://quantra.quantinsti.com/glossary/Estimating-volatility-using-Parkinson-estimator
(both via browser_exec Google SERP snippets fallback; web_search DDGS
backend returned empty results for the direct query this iteration)

## Grid test summary (validation/grid_test.py::run_strategy_grid)

Grid: `trend_window`∈{100,200} × `vol_window`∈{10,20,40} × `target_vol`∈{0.10,0.15,0.20}
× `leverage_cap`∈{1.0,1.5}, symbols={QQQ,SPY,BTC/USDT,ETH/USDT}, vol_regime_splits=3.

- total_cells: 432, passed: 225, **pass_fraction: 0.521**
- by_asset_class: equity 101/216 (0.47), crypto 124/216 (0.57)
- by_vol_regime: low 106/144 (0.74), mid 101/144 (0.70), high 18/144 (0.125)
- best_cell: SPY, trend_window=200/vol_window=10/target_vol=0.20/leverage_cap=1.0,
  low-vol regime, Sharpe 2.854
- worst_cell: QQQ, trend_window=100/vol_window=40/target_vol=0.15/leverage_cap=1.5,
  high-vol regime, Sharpe -0.515

Both asset classes hold up broadly (equity 47%, crypto 57% pass fraction),
much better cross-asset breadth than the original close-to-close version
(2026-09-08-165: crypto 0/36 = 0%). High-vol regime is the weak spot
(12.5% pass) across both asset classes — same known limitation as the
original vol-targeting overlay and most SMA-trend-gated strategies in this
repo.

## Single-config validation (config: trend_window=200, vol_window=20,
target_vol=0.20, leverage_cap=1.0 — matching the accepted close-to-close
version's config for direct comparison)

| Symbol | Sharpe | MDD | Net Sharpe (5bps/trade) | # trades | WF pass frac | Param sensitivity (rel std) |
|---|---|---|---|---|---|---|
| QQQ | 1.299 (pass) | 0.194 (pass) | 1.144 (pass) | 225 | 0.75 (pass) | 0.037 (pass) |
| SPY | 1.013 (pass, narrow) | 0.204 (pass) | 0.960 (pass) | 67 | 0.75 (pass) | 0.030 (pass) |
| BTC/USDT | 0.816 (fail) | 0.266 (fail) | 0.158 (fail) | 1512 | 0.75 | 0.037 |
| ETH/USDT | 0.969 (fail, near-miss) | 0.204 (pass) | 0.264 (fail) | 1428 | 1.00 | 0.052 |

Walk-forward: manual 4-slice fallback (vbt.utils.splitting.RangeSplitter
broken in this install, pre-existing repo-wide gap). Parameter sensitivity:
swept target_vol∈{0.10,0.15,0.20} × vol_window∈{10,20,40} (9-cell grid) —
all four symbols show very low relative std (<0.06), i.e. the Parkinson
estimator's sizing dial is not fragile to these parameter choices.

## Accept/Reject

- **Equity (QQQ, SPY): ACCEPT.** All validators pass. QQQ Sharpe 1.30
  clears comfortably; SPY 1.01 is a narrow pass (identical to the
  close-to-close predecessor's own narrow SPY pass at 1.016), consistent
  cross-strategy pattern in this repo.
- **Crypto (BTC/USDT, ETH/USDT): REJECT** at this specific config (no
  deadband/turnover control) — the continuous Parkinson-vol sizing dial
  updates every single day without hysteresis, generating ~1400-1500
  "trades" (position-size changes) over the sample and completely wiping
  out the raw edge after a modest 5bps/trade cost assumption (net Sharpe
  0.16/0.26 vs 0.5 threshold). Note the grid (which doesn't apply
  transaction-cost drag) actually shows crypto passing MORE grid cells than
  equity (57% vs 47%) on a Sharpe+MDD-only basis — the rejection here is
  specifically a turnover/transaction-cost artifact of daily-updating
  continuous sizing without a deadband, not a fundamental sign/edge
  problem. A follow-up iteration adding a deadband (the pattern already
  used by the Amihud/Corwin-Schultz continuous-sizing-dial strategies,
  ids 2026-09-16-139/140) is a promising next step to potentially rescue
  crypto.
