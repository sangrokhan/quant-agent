# DeMarker (DeM) Bullish-Divergence Long — Backtest Report

**Status: REJECTED** (Sharpe validator fails on best-config; param-sensitivity
degenerate on the same grid)

## Hypothesis

Source: https://tradersunion.com/interesting-articles/forex-indicators-for-traders/demarker-indicator/
(divergence-spotting section). DeMarker = SMA(DeMax,n)/(SMA(DeMax,n)+SMA(DeMin,n)),
DeMax = max(high_t - high_{t-1}, 0), DeMin = max(low_{t-1} - low_t, 0), default
n=14, overbought/oversold at 0.70/0.30. Bullish divergence: price makes a
lower swing low while DeMarker makes a higher low at the same bar (selling
pressure fading despite the new low). This repo already has a DeMarker
threshold-crossing oversold-bounce strategy (2026-09-04-154, accepted
narrowly on QQQ), but no divergence construction had been tested — same
indicator family, distinct technique, following this repo's established
swing-low-divergence pattern (BOP/A-D-Line/Elder-Ray/MFI divergence entries).

Entry: bullish divergence confirmed at a swing low AND DeMarker < oversold_gate
(0.30, source's oversold zone). Exit: close crosses above exit_sma_window(20)
SMA, or max_hold_days(15) time-stop.

## Grid test (Step 6)

`param_grid={"dem_window": [10,14,20], "swing_window": [3,5], "oversold_gate": [0.25,0.30]}`,
symbols equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3.
144 total cells.

- **pass_fraction**: 0.222 (32/144)
- **by_asset_class**: equity 25/72 (0.347), crypto 7/72 (0.097)
- **by_vol_regime**: low 0/48, mid 15/48, high 17/48
- **best_cell**: dem_window=14, swing_window=3, oversold_gate=0.30, QQQ,
  high-vol regime, Sharpe 1.485
- **worst_cell**: dem_window=20, swing_window=5, oversold_gate=0.25,
  ETH/USDT, low-vol regime, Sharpe 0.258

Reading: strongest in equity high/mid-vol regimes; essentially absent in
low-vol regimes across both asset classes; crypto much weaker than equity
overall (only 7/72 passing cells, mostly in high-vol).

## Single-config validation (best cell params, full QQQ 2019-2026 sample)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.923 | ≥ 1.0 |
| Max drawdown | PASS | 0.0706 | ≤ 0.25 |
| Transaction-cost survival (10bps/trade, 6 trades) | PASS | net Sharpe 0.911 | ≥ 0.5 |
| Walk-forward (manual 4-equal-slice fallback; vbt.utils.splitting.RangeSplitter broken in this install) | PASS | 4/4 splits positive Sharpe (1.0) | ≥ 0.75 |
| Parameter sensitivity (12-combo grid, dem_window×swing_window×oversold_gate on QQQ) | **FAIL** | degenerate (NaN relative_std; one/more grid cells produced a zero-variance/infinite-mean Sharpe artifact, likely near-zero-trade cells) | ≤ 0.5 |

Note: the grid's own best-cell Sharpe (1.485, high-vol regime slice) is
above 1.0, but that's the vol-regime-tercile subsample; the full-sample
single-config Sharpe (0.923, matching QQQ overall across all regimes) is
what the standard validator checks and it falls short. Very low trade count
(6 trades over ~7.5 years) makes both the Sharpe estimate and the
parameter-sensitivity sweep noisy/unstable — a structural issue with this
divergence construction's rarity, not just unlucky parameters.

## Decision

**REJECT.** Sharpe validator fails on full-sample best-config (0.923 vs 1.0
threshold) and parameter-sensitivity is degenerate/unstable due to very low
trade counts across the grid. Consistent with repo's other borderline
divergence variants — narrow, low-frequency setups that don't clear the
bar. Equity/high-vol slice is a near-miss (Sharpe 1.485) worth revisiting
if a future iteration wants to add a high-vol regime gate explicitly rather
than trading unconditionally.
