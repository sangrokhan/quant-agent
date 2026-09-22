# DXY-BTC Rolling Correlation Breakdown Regime Filter

**Date:** 2026-09-23 | **Strategy file:** `strategies/2026-09-23_dxy_btc_correlation_breakdown.py`

## Hypothesis

Per a TradingView "Correlations" indicator SERP snippet ("Correlation
Breakdown Detection: Short-term correlation (35 bars) compared against
long-term correlation (100 bars)") and Matrixport BIT Knowledge Hub's
framing ("DXY-Bitcoin inverse correlation has historically been strongest
in moderate environments... acute dollar [stress]... correlation
breakdown"), this repo's first DXY angle to use ROLLING CORRELATION (not
absolute level or rate-of-change, both already tested) as the regime
signal: trade a simple SMA(50) trend-following signal only when the
short-window (35-bar) correlation of asset-returns vs DXY-returns is more
negative than the long-window (100-bar) baseline correlation minus a
buffer -- i.e. only trade when the DXY inverse relationship is currently
"intact" per the source's framing.

## Grid summary (`grid_summary_dxy_btc_correlation_breakdown.json`)

- 96 cells: `short_window` in {20,35} x `long_window` in {80,100} x
  `buffer` in {0.0,0.1} x `trend_window`={50}, QQQ/SPY/BTCUSDT/ETHUSDT,
  vol_regime_splits=3.
- **pass_fraction: 0.3125 (30/96)**
- by_asset_class: equity 17/48, crypto 13/48.
- by_vol_regime: low 27/32, mid 3/32, **high 0/32** (decisive high-vol
  failure, consistent with nearly every trend-filter strategy in this repo).
- best_cell: QQQ, short_window=20, long_window=80, buffer=0.1, low-vol,
  Sharpe 2.63.

## Single-config validators (best_cell params, full-sample 2018-2026)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.95 (FAIL, thr 1.0) | 0.126 (PASS) | 0.608 (PASS) | 1.0 (PASS) | 0.19 (PASS) |
| SPY | 0.70 (FAIL) | 0.118 (PASS) | 0.277 (FAIL) | 0.75 (PASS, borderline) | 0.09 (PASS) |
| BTC/USDT | 0.14 (FAIL) | 0.486 (FAIL, decisive) | -0.048 (FAIL, 6488 trades) | 0.75 (PASS) | 0.34 (PASS) |

Full-sample Sharpe fails for all three symbols. BTC additionally fails MDD
decisively (0.486 vs 0.25 threshold) and has an extremely high trade count
(6488 over the sample -- correlation-window flip-flopping likely drives
excessive turnover on noisy crypto correlation estimates), making it
uninvestable on realistic transaction costs. As with several prior
regime-gate strategies in this repo, the edge concentrates almost entirely
in the low-vol tercile and does not survive when high-vol periods (0/32
decisive fail) are included in the full sample.

## Decision: REJECTED

All three tested symbols fail the primary Sharpe validator at full-sample
scope. The correlation-breakdown framing did not produce a materially
different (better) outcome than this repo's three prior DXY angles (level,
momentum, absolute hysteresis) -- all four DXY variants now share the same
failure mode: promising low-vol-tercile grid cells that do not generalize
to the full sample once high-vol regimes are included.
