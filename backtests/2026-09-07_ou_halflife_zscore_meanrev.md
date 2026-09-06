# Backtest report: Ornstein-Uhlenbeck half-life-gated Z-score mean reversion

**Strategy file:** `strategies/2026-09-07_ou_halflife_zscore_meanrev.py` (kept as rejected-attempt record; near-miss on SPY)
**Outcome:** REJECTED — SPY passes Sharpe/MDD/TC/walk-forward but fails parameter sensitivity; QQQ fails Sharpe outright; crypto decisive fail.

## Hypothesis

Per QuanterLab's OU-process article
(https://quanterlab.com/articles/stochastic-ou-process): fit a rolling
discrete-time AR(1) to log(price) to obtain mean-reversion speed `theta`,
implied long-run mean `mu`, half-life, and equilibrium std `sigma_eq`. Only
trade when the fitted half-life falls in the source's own "tradable"
5-30-bar sweet spot (their explicit rule of thumb: <5 bars = noise,
>100 bars or negative = not mean-reverting, "walk away"). Entry when
z=(X-mu)/sigma_eq < -entry_z; exit on z crossing back toward zero, regime
break (half-life leaves the window), or a time-stop. Distinct from existing
`zscore_meanrev` strategies in this repo which use simple rolling mean/std
z-scores with no fitted reversion-speed gate.

## Grid test summary (Step 6)

`param_grid={"lookback": [40,60,90], "entry_z": [1.0,1.5,2.0]}`,
`symbols={"equity": [QQQ, SPY], "crypto": [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3`, period 2019-01-01 to 2026-09-01 (108 cells).

- **pass_fraction: 0.065** (7/108 cells) — very weak across the grid overall
- **by_asset_class:** equity 7/54 passed; crypto **0/54** (decisive reject)
- **by_vol_regime:** low 1/36; mid 4/36; high 2/36 — no clear regime concentration (unlike the APZ/BB pattern), suggesting this isn't simply a low-vol-only effect but a narrow, unstable edge overall
- **best_cell:** lookback=40, entry_z=1.5, SPY, high-vol regime, Sharpe 1.86

## Single-config validation (Step 7) — best grid config (lookback=40, entry_z=1.5), full sample

| Symbol | Sharpe (thr 1.0) | Max DD (thr 0.25) |
|---|---|---|
| QQQ | 0.415 FAIL | 0.076 PASS |
| SPY | 1.373 PASS | 0.054 PASS |

SPY full validator suite (lookback=40, entry_z=1.5):
- Sharpe: 1.373 PASS (thr 1.0)
- Max drawdown: 0.054 PASS (thr 0.25)
- Transaction cost survival (10bps/trade, 42 trades): net Sharpe 1.101 PASS (thr 0.5)
- Walk-forward (manual 4-slice split, workaround for the known `vbt.utils.splitting` API bug documented in prior reports e.g. `2026-09-03_btc_absolute_momentum.md`): splits Sharpe [0.57, 2.16, 2.26, -0.14] → 3/4 positive → pass_fraction 0.75 PASS (thr 0.75)
- Parameter sensitivity (entry_z sweep at lookback=40: {1.0: 0.436, 1.5: 1.373, 2.0: 0.435}): relative_std 0.590 **FAIL** (thr 0.5) — Sharpe collapses by ~68% moving entry_z one notch off the peak in either direction; the SPY result is a narrow spike rather than a robust plateau.

## Conclusion

**Rejected.** SPY looks attractive at the single best-grid-config level (all
of Sharpe/MDD/TC/walk-forward pass), but the parameter sensitivity check
correctly flags it as a fragile peak — entry_z=1.5 is a local optimum
surrounded by much weaker settings (1.0 and 2.0 both give Sharpe ~0.43,
below threshold), which is a classic overfitting signature for a strategy
tuned specifically to match SPY's realized vol scale over this exact sample.
QQQ fails outright on the same config, and crypto is a decisive 0/54 across
the whole grid. Overall grid pass_fraction (0.065) is also far too low to
support a broad accept.

Worth noting for future loops: unlike the three band-mean-reversion
strategies tested so far (BB, Keltner, APZ — all "works only in low-vol
regime"), this OU strategy's passes are spread across all three vol regimes
(low/mid/high all have some passes), suggesting the OU half-life gate is
filtering on a genuinely different axis than realized-vol regime. A future
iteration could try widening the half-life sweet-spot search (this run only
tried lookback in [40,60,90]; the source suggests half-life estimates need
a large enough lookback relative to the half-life itself for statistical
reliability) or testing on a pairs-trading spread (the source's own stated
best-fit use case) rather than an outright price series, since OU fits
residuals/spreads much better than raw non-stationary price series.
