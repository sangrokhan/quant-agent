# Backtest Report: GMMA Ribbon Compression-Breakout

**Strategy file:** `strategies/2026-09-10_gmma_ribbon_compression_breakout.py`
**Date:** 2026-09-10
**Outcome:** REJECTED

## Hypothesis

Per StockCharts ChartSchool's GMMA guide, the Guppy Multiple Moving Average
is a 12-EMA ribbon (short group: 3,5,8,10,12,15; long group: 30,35,40,45,
50,60). Source's rule: bullish signal when the short-term ribbon crosses
above the long-term ribbon; ribbon compression (narrow gap) often precedes
a significant breakout. Tested: long entry when the mean of the short-group
EMAs crosses above the mean of the long-group EMAs, gated by the ribbons
having been compressed (gap <= compression_threshold) within a trailing
lookback window before the cross. First GMMA strategy in this repo.

## Step 6 grid summary

Grid: `compression_threshold` in {0.02, 0.04} x `max_hold_days` in
{20, 40} x QQQ/SPY/BTC/ETH x low/mid/high realized-vol terciles (48
cells, 2018-01-01 to 2024-12-31). Fixed `compression_lookback=20`.

- pass_fraction: 0.167 (8/48)
- by_asset_class: equity 8/24, crypto 0/24 (decisive crypto fail)
- by_vol_regime: low 8/16, mid 0/16, high 0/16 — edge concentrated
  entirely in low-vol regime
- Best cell: compression_threshold=0.02, max_hold_days=40, QQQ, low-vol
  tercile, Sharpe 2.29 (SPY same config, low-vol, 1.72)
- Note: 0.02 vs 0.04 compression_threshold produced identical results —
  the compression gate rarely binds at these thresholds given the ribbon's
  typical gap range, so it's effectively acting as a near-unconditional
  ribbon crossover rather than meaningfully filtering for compression.

## Step 7 single-config validation (compression_threshold=0.02, compression_lookback=20, max_hold_days=40, full sample 2018-2024)

| Metric | QQQ | SPY | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 0.651 | 0.595 | >= 1.0 | No / No |
| Max drawdown | 0.194 | 0.166 | <= 0.25 | Yes / Yes |
| TC survival (5bps/trade) | 0.610 | 0.540 | >= 0.5 | Yes / Yes |
| Walk-forward (4 splits) | 0.75 (3/4) | 0.50 (2/4) | >= 0.75 | Yes / No |
| Parameter sensitivity | 0.162 | 0.051 | <= 0.5 | Yes / Yes |

Trade counts (entries only): QQQ 25, SPY 25 over ~7 years.

## Decision: REJECTED

Full-sample Sharpe misses the 1.0 threshold on both symbols (0.651/0.595)
despite an attractive tercile-conditioned best cell (QQQ 2.29, SPY 1.72 in
low-vol) — that low-vol-only edge does not survive full-sample aggregation
across all vol regimes. SPY additionally fails walk-forward (only 2/4
splits Sharpe-positive). The compression gate as implemented (threshold
0.02/0.04) turned out not to meaningfully filter signals (identical results
at both thresholds), so this is effectively an unfiltered ribbon-average
crossover, and that raw crossover isn't strong enough on its own.

## Source

- https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/moving-average-trading-strategies/guppy-multiple-moving-average-an-ma-ribbon-designed-to-tip-the-markets-hand
