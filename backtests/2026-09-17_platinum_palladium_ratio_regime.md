# Platinum/Palladium Ratio Z-Score Regime Filter — Backtest Report

**Hypothesis:** PPLT/PALL price ratio rolling z-score crossing above/below
thresholds signals a precious-metals risk regime; long (risk-on) when
z-score falls low enough (platinum cheap vs palladium), flat (risk-off)
when z-score rises high enough (platinum expensive vs palladium), holding
prior state in between (hysteresis). Mirrors the already-accepted GLD/SLV
ratio regime filter (2026-09-05-030) construction but applied to a
genuinely distinct pair driven by auto-catalyst industrial substitution
economics rather than investment demand.

**Source:** https://www.goldpriceforecast.com/explanations/platinum-to-palladium-ratio
(historical range 0.6-5.3, average ~2.8 since 1990; "if the ratio moves to
extremes, it creates a trading opportunity").

**Strategy file:** `strategies/2026-09-17_platinum_palladium_ratio_regime.py`

## Step 6 — Grid test summary (param_grid: ratio_lookback in [126,252] x
low_z_threshold in [-1.5,-1.0] x high_z_threshold in [1.0,1.5]; symbols:
equity QQQ/SPY, crypto BTC/USDT, ETH/USDT; vol_regime_splits=3; period
2019-01-01..2026-09-01)

- total_cells: 96, passed_cells: 24, **pass_fraction: 0.25**
- by_asset_class: equity 24/48 (50%), crypto 0/48 (0%)
- by_vol_regime: low 16/32, mid 8/32, high 0/32 -- concentrated in
  low/mid-vol only (unlike GLD/SLV's low+high split), a weaker signature.
- best_cell (per-regime slice): ratio_lookback=126, low_z=-1.0,
  high_z=1.0, QQQ, low-vol regime, Sharpe=2.56 -- but this is a per-regime
  slice metric, not representative of full-sample performance.

## Step 7 — Single-config validators (best grid config,
ratio_lookback=126, low_z_threshold=-1.0, high_z_threshold=1.5, FULL
sample period, not regime-sliced)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | **FAIL** 0.694 | **FAIL** 0.542 |
| Max Drawdown (<= 0.25) | **FAIL** 0.298 | **FAIL** 0.341 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade, 12 trades) | PASS 0.684 | PASS 0.529 |
| Parameter sensitivity (relative_std <= 0.5, 27-cell sweep) | PASS 0.325 | PASS 0.283 |

Walk-forward not run (pre-existing `vbt.utils.splitting` AttributeError
bug in this repo's installed vectorbt version, same documented gap as
other entries).

## Outcome: **REJECTED**

The grid's per-vol-regime slices looked promising (up to Sharpe 2.56 in
isolated low-vol windows), but the full-sample Sharpe (0.69 QQQ / 0.54
SPY) and max drawdown (0.30 QQQ / 0.34 SPY) both fail decisively when
evaluated over the whole 2019-2026 period rather than sliced by regime --
the strategy is only "on" during a favorable subset and gives back gains
(or worse) elsewhere, unlike the GLD/SLV ratio filter which passed
full-sample validators cleanly at 59% grid pass fraction and both
low+high vol regime coverage. Platinum/palladium's ratio dynamics (driven
by episodic industrial-substitution supply shocks, e.g. the 2000-2001
Russia palladium-supply scare cited in the source) appear to make the
regime-gate framing less stable than gold/silver's more liquid,
investment-driven ratio. Not pursuing a crypto rescue given the equity
full-sample failure already disqualifies the primary config.
