# Coefficient of Variation (CV) Inverse Sizing on SMA(200) Trend Gate

**Hypothesis:** Per https://alphax.trading/dictionary/coefficient-of-variation
(read via browser_exec; web_extract backend cannot fetch page content, only
search): Coefficient of Variation CV = std(returns) / mean(returns), a
normalized "risk per unit of return" measure. Unlike every Sharpe-family
ratio already tested in this repo (excess-return numerator over a risk
denominator, higher=better, scaled UP with the ratio), CV inverts the
fraction (std/mean, no excess-return subtraction) and is scaled INVERSELY
(exposure = clip(cv_reference / trailing_CV, 0, leverage_cap)) — lower noise-
to-trend ratio implies higher exposure. First Coefficient-of-Variation-based
sizing overlay in this repo.

**Source:** https://alphax.trading/dictionary/coefficient-of-variation

## Grid test summary (equity: SPY/QQQ, crypto: BTC/USDT/ETH/USDT;
cv_window in [40,60,90], cv_reference in [3.0,5.0,8.0]; vol_regime_splits=3)

- total_cells: 108, passed_cells: 26, pass_fraction: 0.241
- by_asset_class: equity 26/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 8/36, high 0/36
- best_cell: SPY, cv_window=40, cv_reference=8.0, low-vol, Sharpe=2.788
- worst_cell: QQQ, cv_window=60, cv_reference=3.0, high-vol, Sharpe=-0.844

## Single-config validator results (best full-sample config from sweep:
cv_window=40, cv_reference=8.0, trend_window=200, leverage_cap=1.0)

| Symbol | Sharpe | Passed | MDD | Passed | Net Sharpe (5bps/trade) | Passed | Walk-fwd frac | Passed | Param sens (rel std) | Passed |
|---|---|---|---|---|---|---|---|---|---|---|
| SPY | 0.830 | No (thr 1.0) | 0.140 | Yes | 0.789 | Yes (thr 0.5) | 0.75 | Yes | 0.174 | Yes |
| QQQ | 1.288 | Yes (thr 1.0) | 0.191 | Yes | 1.273 | Yes (thr 0.5) | 0.75 | Yes | 0.292 | Yes |

Note: `validators.check_walk_forward` has a pre-existing tooling gap
(`vbt.utils.splitting.RangeSplitter` unavailable, seen previously e.g.
2026-09-13 Treynor entry) — substituted a manual 4-split walk-forward
(positive full-sample-Sharpe-per-split, same 0.75 pass-fraction threshold)
for both symbols; both hit exactly 3/4 splits positive.

## Decision

**Accepted (QQQ only).** All 5 validators pass for QQQ at cv_window=40,
cv_reference=8.0. SPY fails only the Sharpe threshold (0.830 < 1.0) though
every other validator passes comfortably — a near-miss, not a decisive
rejection; worth revisiting SPY with a wider cv_window sweep in a future
iteration. Crypto (BTC/USDT, ETH/USDT) rejected decisively across the whole
grid (0/54 cells) — consistent with nearly every other sizing-overlay family
tested this cron trigger underperforming on crypto's higher-vol/higher-CV
regime.
