# Backtest Report: GARCH(1,1) Volatility-Targeting Continuous Sizing

**Strategy file:** `strategies/2026-09-21_garch_vol_targeting_continuous_sizing.py`
**Knowledge base id:** 2026-09-21-238

## Hypothesis

Per https://marketmaker.cc/en/blog/post/volatility-targeting-garch-strategy/
(read via browser_exec fallback; web_extract's ddgs backend cannot extract
page content), volatility targeting sizes exposure as
`w_t = vol_target / sigma_hat_t` (capped), where `sigma_hat_t` is a
one-step-ahead volatility *forecast*. The article cites Moreira & Muir
(2017) showing this style of inverse-vol scaling raises Sharpe and
compresses drawdowns because volatility clusters (forecastable) while
returns don't.

This repo already has a binary GARCH(1,1) long/flat regime gate
(2026-09-07-015, rejected: Sharpe near-miss) and a family of realized-vol
(trailing rolling std) continuous sizing overlays (2026-09-08-165 and
descendants, several accepted). This strategy is the first to combine a
genuinely-fitted GARCH(1,1) conditional-variance forecast (reacts to a
shock immediately via the alpha term, not lagged into a rolling window)
with CONTINUOUS sizing rather than a binary switch.

## Single-config validation (best grid cell: vol_target=0.20, refit_every=42, leverage_cap=1.0)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Param sensitivity (rel std) |
|---|---|---|---|---|
| QQQ | 0.998 (fail, thr 1.0) | 0.282 (fail, thr 0.25) | 0.982 (pass) | 0.021 (pass) |
| SPY | 0.960 (fail) | 0.218 (pass) | 0.947 (pass) | 0.057 (pass) |
| BTC/USDT | 0.730 (fail) | 0.383 (fail) | 0.717 (pass) | 0.068 (pass) |
| ETH/USDT | 0.717 (fail) | 0.385 (fail) | 0.706 (pass) | 0.075 (pass) |

Walk-forward: not run (pre-existing `vbt.utils.splitting` AttributeError bug
in this repo's vectorbt version, same known issue affecting 2026-09-07-015).

## Grid summary (Step 6)

Grid: `param_grid={vol_target:[0.10,0.15,0.20], refit_every:[42], leverage_cap:[1.0,1.5]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01, 72 cells.

- **pass_fraction: 0.417 (30/72)**
- by_asset_class: equity 18/36 (50%), crypto 12/36 (33%)
- by_vol_regime: low 18/24 (75%), mid 6/24 (25%), high 6/24 (25%)
- best_cell: SPY, vol_target=0.20/leverage_cap=1.0, low-vol regime, Sharpe 2.564
- worst_cell: SPY, vol_target=0.15/leverage_cap=1.5, mid-vol regime, Sharpe 0.052

The edge is mechanically concentrated in the low-vol tercile, as expected
for an inverse-vol sizing dial (bigger exposure exactly when vol is calm) —
but that per-cell picture doesn't translate into a full-sample pass on the
primary single-config validators above.

## Decision

**Rejected.** The GARCH-forecast's faster shock response did not
meaningfully outperform this repo's simpler realized-vol-window sizing
family on the primary full-sample validators, mirroring the earlier finding
that fitted GARCH added no edge over trailing-window regime filters
(2026-09-07-015).
