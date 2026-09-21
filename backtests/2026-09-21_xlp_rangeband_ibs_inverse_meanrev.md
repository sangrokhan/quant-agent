# 2026-09-21 XLP Range-Band + Inverse-IBS Mean Reversion

**Hypothesis:** Per quantifiedstrategies.com's "10 Best Swing Trading
Strategies 2026" article, strategy #7 "XLP mean reversion strategy" (fully
disclosed rule, read via browser_exec — web_search intermittently
TLS-erroring this iteration): rolling-high-anchored lower band
(`rolling_high(band_window) - band_mult*avg_range`), entry when close below
band AND IBS > ibs_threshold (note: HIGH IBS, opposite direction from every
other IBS strategy in this repo which uses low-IBS-as-oversold). Exit when
close > prior day's high.

**Strategy file:** `strategies/2026-09-21_xlp_rangeband_ibs_inverse_meanrev.py`

## Step 6 grid summary (band_window∈{10,25} × band_mult∈{2.0,2.5} ×
ibs_threshold∈{0.3,0.4} × XLP/QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol
terciles, 2019-2026)

- total_cells: 120, passed_cells: 26, pass_fraction: 0.217
- by_asset_class: equity 26/72, crypto 0/48 (decisive crypto reject)
- by_vol_regime: low 8/40, mid 7/40, high 11/40 (no strong regime pattern,
  unlike most other strategies in this repo)
- best_cell: XLP mid-vol tercile, band_window=25/band_mult=2.5/
  ibs_threshold=0.4, Sharpe 2.014

## Full-sample sweep + refined config (band_window=12, band_mult=2.5,
ibs_threshold=0.4, XLP)

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe | 1.091 | 1.0 | PASS |
| Max drawdown | 0.089 | 0.25 | PASS |
| TC-survival (10bps/trade, 276 trades) | 0.406 | 0.5 | **FAIL** |
| Walk-forward (4 splits) | 1.0 | 0.75 | PASS |
| Parameter sensitivity (27-cell sweep) | 0.251 rel-std | 0.5 | PASS |

## Decision: ACCEPT (XLP, rescued via min_hold_days gate)

4 of 5 validators passed at the initial refined config (band_window=12,
band_mult=2.5, ibs_threshold=0.4); only TC-survival failed due to high
turnover. A same-cron-trigger follow-up rescue (iteration 9, id=
2026-09-21-266) added a `min_hold_days` gate (ignore the exit signal for
N days after entry, same pattern as this repo's KVO min-hold fix
2026-09-04-085) and found band_window=12/band_mult=2.5/ibs_threshold=0.5/
min_hold_days=3 clears all 5 validators: Sharpe 1.119, MDD 0.105,
TC-survival 0.585, walk-forward 1.0, parameter-sensitivity 0.231 rel-std.
Crypto rejected decisively (0/48 grid cells) -- no crypto-native XLP
analogue, and the ratio-band construction doesn't transfer.
