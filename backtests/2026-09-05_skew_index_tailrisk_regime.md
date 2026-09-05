# CBOE SKEW Index Extreme-Tail-Risk Regime Filter — Backtest Report

**Hypothesis:** Rolling z-score of the CBOE SKEW index >= extreme_z_threshold
(SKEW abnormally elevated vs its own trailing history -- market paying up
for crash/tail protection) signals a regime worth going flat in; long
otherwise.

**Source:** https://ecmsource.com/volatility-skew-and-smile-explained-why-otm-puts-cost-more/
(citing Cboe SKEW whitepaper, 2010) -- gives the SKEW formula and historical
range/modal values, but explicitly flags "treating SKEW as a timing signal"
as a common mistake since high SKEW appears in both calm and panicky VIX
regimes. This backtest tests the narrower/mechanical claim (extreme
*relative* SKEW readings, not absolute level) anyway.

**Strategy file:** `strategies/2026-09-05_skew_index_tailrisk_regime.py`

## Step 6 — Grid test summary (param_grid: extreme_z_threshold in
[1.0, 1.5, 2.0] x skew_lookback in [126, 252]; symbols: equity QQQ/SPY,
crypto BTC/USDT, ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 72, passed_cells: 13, **pass_fraction: 0.181**
- by_asset_class: equity 13/36 (36%), crypto 0/36 (0%) -- again, the
  SPX-options-derived signal has zero transfer to crypto.
- by_vol_regime: low 12/24, mid 1/24, high 0/24 -- only works in low-vol
  slices.
- best_cell: extreme_z_threshold=2.0, skew_lookback=126, SPY, low-vol
  regime, Sharpe=2.29 (single vol-regime slice, not full-period).

## Step 7 — Single-config validators (best grid config over FULL period:
extreme_z_threshold=2.0, skew_lookback=126, min_hold_days=5)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | FAIL 0.919 | FAIL 0.876 |
| Max Drawdown (<= 0.25) | FAIL 0.358 | FAIL 0.341 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade, 46 trades) | PASS 0.884 | PASS 0.834 |
| Parameter sensitivity (relative_std <= 0.5, 6-cell SPY sweep) | PASS 0.126 | n/a |

Walk-forward not run (pre-existing `vbt.utils.splitting` AttributeError bug
in this repo's installed vectorbt version, consistent with other entries).

## Outcome: **REJECTED**

Full-period Sharpe and max drawdown both fail on both QQQ and SPY at the
best grid config -- the attractive Sharpe=2.29 in the grid's best_cell was
only within the low-vol-regime tercile slice, not representative of the
strategy's full-period behavior. Consistent with the source's own warning
that SKEW is not a reliable standalone timing signal: the mechanical
"flat during extreme relative SKEW" rule does reduce risk somewhat in
low-vol stretches specifically, but doesn't produce a full-period edge over
buy-and-hold once mid/high-vol periods are included. Crypto again shows zero
transfer (0/36). Not worth revisiting without pairing with an independent
trend/vol filter that's already doing the heavy lifting in non-low-vol
regimes.
