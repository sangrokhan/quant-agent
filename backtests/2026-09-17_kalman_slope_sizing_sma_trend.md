# 2026-09-17 Kalman-Filter Slope Continuous Sizing Dial + SMA Trend Gate

## Hypothesis

Per Quantitativo's "Fast trend following" (https://www.quantitativo.com/p/fast-trend-following,
read this iteration): a single constant-velocity 1D Kalman filter (level +
slope state) applied to close price gives a smoother, lower-lag trend
estimate than a moving average; the filter's own estimated SLOPE state is a
naturally continuous trend-strength/direction signal. This repo has 8 prior
Kalman-filter entries, all binary crossover/breakout/mean-reversion
triggers (2026-09-05-056 dual-Kalman percentile breakout rejected;
2026-09-08-052 single Kalman level+slope binary crossover also rejected).
This iteration reframes the SAME Kalman level+slope filter as a CONTINUOUS
SIZING dial: the filter's slope, rolling-z-scored and tanh-squashed, scales
exposure smoothly within an SMA(trend_window) uptrend gate -- following
this repo's now-established "binary oscillator -> continuous sizing dial"
rescue pattern (previously successful for DPO, Hurst, VHF, TII, RVI,
MAMA-FAMA spread, etc).

Source: https://www.quantitativo.com/p/fast-trend-following

## Strategy file

`strategies/2026-09-17_kalman_slope_sizing_sma_trend.py`

## Grid test summary (216 cells: sensitivity x zscore_window x deadband x 4 symbols x 3 vol regimes)

- pass_fraction: 0.505 (109/216)
- by_asset_class: equity 62/108 passed; crypto 47/108 passed
- by_vol_regime: low 69/72; mid 26/72; high 14/72 (as usual, low-vol regime dominates passes)
- best_cell: QQQ, sensitivity=0.4/zscore_window=90/deadband=0.1, low-vol regime, Sharpe 2.68

## Single-config validation (full sample, 2019-01-01 to 2026-09-01)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe, 5bps/trade) | Walk-forward (4-split, >0 Sharpe fraction) | Param sensitivity (relative std, sensitivity +/-30%) | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | deadband=0.2, sensitivity=0.4, zscore_window=60 | 1.240 (>=1.0 pass) | 0.114 (<=0.25 pass) | 0.858 (>=0.5 pass) | 1.0 (>=0.75 pass) | 0.051 (<=0.5 pass) | **ACCEPT** |
| SPY | deadband=0.2, sensitivity=0.4, zscore_window=40 | 1.149 (>=1.0 pass) | 0.062 (<=0.25 pass) | 0.637 (>=0.5 pass) | 1.0 (>=0.75 pass) | 0.045 (<=0.5 pass) | **ACCEPT** |
| BTC/USDT | deadband=0.1, sensitivity=0.4, zscore_window=60, leverage_cap=0.3 | 0.163 (<1.0 **FAIL**) | 0.206 (<=0.25 pass) | -0.057 (<0.5 **FAIL**) | 1.0 (>=0.75 pass) | 0.004 (<=0.5 pass) | **REJECT** |

## Outcome

**Accepted for equity (QQQ, SPY)** -- all 5 validators pass for both
symbols with comfortable margin. **Rejected for crypto** -- BTC/USDT fails
decisively on Sharpe and transaction-cost survival at the grid-best crypto
config; the earlier low-leverage-cap "rescue" pattern used successfully for
other continuous-sizing strategies in this repo (e.g. MAMA-FAMA, Hurst) did
not close the gap here (still short of the 1.0 Sharpe threshold even at the
grid-optimal cell).

Scope: this strategy is honestly narrower than the full grid's raw
pass-fraction suggests -- it works reliably on equity index ETFs (QQQ/SPY)
in low-to-mid volatility regimes but should not be trusted on crypto or in
high-vol regimes without further work.
