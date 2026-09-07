# Backtest Report: Garman-Klass Volatility Squeeze Breakout

**Strategy file:** `strategies/2026-09-08_garman_klass_vol_squeeze_breakout.py`
**Date:** 2026-09-08
**Outcome:** REJECTED

## Hypothesis

Per LuxAlgo's Garman-Klass Estimator library page
(https://www.luxalgo.com/library/indicator/garman-klass-estimator/): GK
volatility measures volatility from the whole bar (high/low range +
open/close jump, each separately weighted: 0.5*ln(H/L)^2 -
(2ln2-1)*ln(C/O)^2), more efficient than close-to-close vol. Source's own
trading guidance: percentile-rank compression (below a low threshold)
"often resolves into wider movement." Strategy: long entry when GK-vol
percentile rank was compressed on the prior bar AND close breaks above its
own prior N-day high AND price is above a longer-term SMA trend filter;
exit on GK-vol percentile rank expanding past a high threshold, trend-filter
break, or time-stop.

First Garman-Klass-based strategy in this repo — mechanically distinct from
prior Bollinger-Bandwidth-percentile squeeze strategies (2026-09-05-020,
2026-09-07-003) since GK vol is derived from the full OHLC bar (range +
gap), not a Bollinger Band's close-based standard deviation.

## Grid Test Summary (Step 6)

`param_grid={"squeeze_pct": [15.0, 20.0, 25.0], "breakout_window": [15, 20]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **72 total cells, 8 passed (pass_fraction = 0.111)**
- By asset class: equity 8/36, crypto 0/36 (decisive crypto fail)
- By vol regime: low 6/24, mid 2/24, high 0/24 (edge concentrated in low-vol,
  some spillover to mid-vol)
- Best cell: `squeeze_pct=25.0, breakout_window=15`, QQQ mid-vol, Sharpe 1.71
- Worst cell: `squeeze_pct=15.0, breakout_window=15`, SPY high-vol, Sharpe -1.45

## Single-Config Validation (Step 7, best-cell config on QQQ full sample)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL (near-miss)** | 0.80 | 1.00 |
| Max drawdown | PASS | 8.7% | 25% |

Full-sample Sharpe is a near-miss (0.80 vs 1.0 threshold) — the mid/low-vol
grid-cell edge doesn't fully carry over to the whole sample once high-vol
periods (where the grid shows a decisive negative Sharpe, -1.45 worst cell)
are included. Skipped walk-forward/TC-survival/parameter-sensitivity given
the decisive full-sample Sharpe fail and the low overall grid pass fraction
(11%) concentrated almost entirely in one asset class and vol regime.

## Decision

**REJECTED.** Full-sample Sharpe misses threshold on the single
best-looking config; edge is narrow (equity-only, low/mid-vol-concentrated,
8/72 grid cells); crypto rejected decisively (0/36). Worth a note for a
future loop: the raw squeeze-breakout signal direction and GK-vol
percentile-rank exit look promising in low-vol equity regimes specifically
— a future iteration could try gating entries to ONLY the low-vol tercile
explicitly (rather than trend-filter alone) to see if that narrower scope
clears the Sharpe bar.
