# Volume-confirmed Darvas Box + SMA Trend Gate + Staircase Trailing Stop

**Date:** 2026-09-23 | **Strategy file:** `strategies/2026-09-23_darvas_box_volconfirm_trend_trail.py`

## Hypothesis

Per https://arongroups.co/forex-articles/darvas-boxes-strategy (Abe Cofnas,
visited this iteration), the original Darvas Box mechanic already tested in
this repo (`2026-09-05-054`, accepted equity QQQ/SPY, decisively rejected
crypto 0/72 grid cells) can plausibly be rescued for crypto by adding the
source's own three explicitly-disclosed mechanical filters not present in
the original implementation:

1. Volume confirmation: breakout-candle volume >= 1.5x the 20-session
   average volume.
2. Trend alignment: close above SMA(50) at breakout.
3. Staircase trailing stop: stop trails up to each new confirmed box's
   bottom (never lowered), replacing the original's fixed time-stop.

## Grid summary (`grid_summary_darvas_volconfirm_trend_trail.json`)

- 96 cells: `high_lookback` in {30,52} x `confirm_days` in {3,5} x
  `volume_mult` in {1.2,1.5} x `sma_window`={50}, QQQ/SPY/BTCUSDT/ETHUSDT,
  vol_regime_splits=3.
- **pass_fraction: 0.4375 (42/96)**
- by_asset_class: equity 24/48, **crypto 18/48** (up from 0/72 in the
  original unmodified strategy — a genuine partial rescue of the prior
  decisive crypto rejection).
- by_vol_regime: low 23/32, mid 19/32, **high 0/32** (decisive high-vol
  failure across the board).
- best_cell: SPY, high_lookback=30, confirm_days=5, volume_mult=1.2,
  low-vol regime, Sharpe 2.51.
- worst_cell: SPY, high_lookback=52, confirm_days=5, volume_mult=1.2,
  high-vol regime, Sharpe -1.25.

## Single-config validators (best_cell params, full-sample 2018-2026)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.95 (FAIL, thr 1.0) | 0.119 (PASS) | 0.844 (PASS) | 1.0 (PASS) | 0.24 (PASS) |
| SPY | 0.38 (FAIL) | 0.127 (PASS) | 0.211 (FAIL) | 1.0 (PASS) | 0.30 (PASS) |
| BTC/USDT | 0.17 (FAIL) | 0.248 (PASS, near threshold) | -0.047 (FAIL, 3822 trades!) | 1.0 (PASS) | 0.22 (PASS) |

Full-sample Sharpe/tx-cost-survival fail for all three symbols — the strong
Sharpe seen in the grid's low-vol tercile cells does not generalize to the
full sample, which mixes in the decisively-failing high-vol regime. BTC's
extremely high trade count (3822 over the sample, likely from noisy
box-reformation cycling on hourly-derived data) makes it economically
un-investable even before considering the Sharpe miss.

## Decision: REJECTED

All three symbols fail the primary Sharpe validator at full-sample scope;
BTC additionally fails tx-cost survival decisively. The volume+trend+trailing-
stop additions DID measurably narrow the crypto gap (0/72 -> 18/48 grid
cells passing) confirming the source's own diagnosed false-breakout problem
was a real contributor, but not enough to clear this repo's full-sample
acceptance bar. A future iteration could try restricting entries to the
already-identified low/mid vol regimes only (an explicit regime gate) as a
more targeted fix.
