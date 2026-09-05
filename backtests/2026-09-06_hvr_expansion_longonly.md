# Backtest Report: Historical Volatility Ratio (HVR) Expansion Long-Only (2026-09-06)

**Strategy file:** `strategies/2026-09-06_hvr_expansion_longonly.py`
**Knowledge base id:** 2026-09-06-109
**Outcome:** REJECTED

## Hypothesis

Historical Volatility Ratio (HVR = rolling std-dev of log returns over a
short period / rolling std-dev over a long period) expansion, adapted
long-only: long when HVR > ratio_threshold (short-term realized vol
expanding relative to its long-term norm), flat otherwise.

## Source

https://doc.stocksharp.com/api-examples/2055_HVR.html (StockSharp "Historical
Volatility Ratio Strategy" example): "Strategy based on the Historical
Volatility Ratio (HVR). It compares short-term volatility over 6 bars to
long-term volatility over 100 bars using log returns. When the ratio rises
above the threshold, the system goes long expecting volatility expansion."
Default params: ShortPeriod=6, LongPeriod=100, RatioThreshold=1.0. Original
source is long/short-symmetric; adapted to long-only per repo convention
(SAFETY.md, no short-selling infrastructure).

First HVR-family strategy in this repo — distinct from all prior
volatility-regime filters (Choppiness Index, Bollinger Bandwidth squeeze,
ATR-expansion breakout, VHF, Random Walk Index) because HVR is a ratio of
two horizon-different realized volatilities of log returns.

## Step 6 grid summary (short_period in [4,6,10], ratio_threshold in
[0.8,1.0,1.3], equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT],
vol_regime_splits=3, 2018-01-01..2026-09-01)

- total_cells: 108, passed_cells: 12, **pass_fraction: 0.111**
- by_asset_class: equity 12/54 passed, crypto 0/54 passed
- by_vol_regime: low 9/36, mid 3/36, high 0/36
- best_cell: SPY, short_period=4, ratio_threshold=0.8, low-vol regime, Sharpe 2.788
- worst_cell: QQQ, short_period=6, ratio_threshold=1.3, low-vol regime, Sharpe -0.520

## Step 7 single-config validation (SPY, short_period=4, long_period=100,
ratio_threshold=0.8, full sample 2018-2026)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.434 | >= 1.0 | FAIL |
| Max drawdown | 0.350 | <= 0.25 | FAIL |
| Transaction cost survival (10bps, 180 trades) | net Sharpe 0.257 | >= 0.5 | FAIL |
| Walk-forward (4 splits) | pass_fraction 1.0 (4/4 positive) | >= 0.75 | PASS |
| Parameter sensitivity (9-cell grid) | relative_std 0.553 | <= 0.5 | FAIL |

## Decision

**REJECTED.** Fails 4 of 5 validators decisively: full-sample Sharpe (0.434)
and net-of-cost Sharpe (0.257) both far below thresholds, max drawdown
(0.350) breaches the 0.25 cap, and parameter sensitivity (relative_std
0.553) shows an unstable edge across the small grid (Sharpe swings from
0.001 to 0.601 across nearby thresholds). At `short_period=4` the strategy
also trades very frequently (180 trades over ~8.5 years), consistent with a
continuous-regime-state signal (position tracks whichever side of the
threshold HVR sits on, no persistence/hysteresis) whipsawing heavily around
the threshold. Only walk-forward passes cleanly. The grid's best cell
(Sharpe 2.79, SPY low-vol) is again a narrow-regime artifact that does not
generalize to the full sample, matching the pattern seen in all three prior
rejections this cron trigger.
