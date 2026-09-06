# Backtest report: Adaptive Price Zone (APZ, Leibfarth 2006) mean reversion

**Strategy file:** `strategies/2026-09-07_apz_leibfarth_meanrev.py` (kept as rejected-attempt record)
**Outcome:** REJECTED — decisive full-sample Sharpe fail on both tested equities.

## Hypothesis

Per TradingView's APZ script description
(https://www.tradingview.com/script/AzkoAdVR/, developed by Lee Leibfarth,
2006): APZ takes a double-smoothed EMA of hl2 as its centerline and a
double-smoothed EMA of the daily high-low range as its adaptive volatility
measure, forming bands at `centerline ± band_pct * vol_smooth`. Hypothesized
mean-reversion edge: close crossing below the lower APZ band signals an
overextended short-term move that reverts back toward the centerline.

This differs mechanically from previously-tested Bollinger Bands (std-dev
of close, single smoothing) and Keltner Channels (single-smoothed ATR
envelope) by using DOUBLE EMA smoothing on both the centerline and the band
width, which should in theory be less noise-reactive.

## Grid test summary (Step 6)

`param_grid={"window": [3,5,8], "band_pct": [1.5,2.0,2.5]}`,
`symbols={"equity": [QQQ, SPY], "crypto": [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3`, period 2019-01-01 to 2026-09-01 (108 cells).

- **pass_fraction: 0.139** (15/108 cells passed sharpe+mdd thresholds)
- **by_asset_class:** equity 15/54 passed; crypto **0/54** (decisive reject on crypto)
- **by_vol_regime:** low 11/36; mid 3/36; high 1/36 — only holds up (barely) in low-vol regimes
- **best_cell:** window=3, band_pct=1.5, SPY, low-vol regime, Sharpe 2.26
- **worst_cell:** window=3, band_pct=1.5, QQQ, mid-vol regime, Sharpe -0.52

## Single-config validation (Step 7) — best grid config (window=3, band_pct=1.5, max_hold_days=10), full sample

| Symbol | Sharpe (thr 1.0) | Pass | Max DD (thr 0.25) | Pass |
|---|---|---|---|---|
| QQQ | 0.247 | No | 0.188 | Yes |
| SPY | 0.240 | No | 0.227 | Yes |

Full-sample Sharpe is decisively below threshold on both symbols despite the
low-vol-regime subset looking attractive in isolation — the grid's headline
"best cell" result does not generalize once mid/high-vol periods are
included, and crypto rejects outright (0/54). Walk-forward / parameter
sensitivity not run given the full-sample Sharpe fail is already decisive
(suggested_workload=max but no value in spending further compute on a
strategy that fails its primary gate this clearly).

## Conclusion

**Rejected.** The APZ double-smoothed band concept only works in a narrow
low-volatility equity slice; across the full historical sample and across
asset classes it underperforms the Sharpe threshold. Worth noting for future
loops: this repo has now tested three band-family mean-reversion strategies
(Bollinger, Keltner, APZ) and all three show the same low-vol-only pattern —
future iterations should consider explicitly restricting any such
band-mean-reversion entry to a pre-filtered low-vol regime (as
2026-09-03_bb_meanrev_qqq_volregime.py already does) rather than testing the
band signal unconditionally across the full sample.
