# Hurst Regime SMA Crossover + Trailing Stop — Backtest Report

**Date:** 2026-09-24 | **id:** 2026-09-24-011

## Hypothesis

Per PyQuantLab's "Can the Hurst Exponent Reliably Identify Price Trends?"
(https://pyquantlab.medium.com/can-the-hurst-exponent-reliably-identify-price-trends-4aaa14ad9dda),
a rolling-window Hurst exponent (classic Rescaled-Range / R-S analysis)
above a threshold indicates a persistent/trending regime. Only taking a
trend-following SMA-crossover entry when the market is confirmed
"trending" by Hurst should filter out whipsaw entries during random-walk
or mean-reverting regimes. Exit via percentage trailing stop
(source's own disclosed exit mechanism -- no indicator-based exit).
Long-only adaptation of the source's long/short system per SAFETY.md.
First Hurst-exponent-family strategy in this repo (zero prior
`"Hurst"` matches in `strategies_index.jsonl` before this entry; a
related-but-distinct prior Lyapunov+Hurst combo entry exists at
id 2026-09-20-150, accepted QQQ only, which additionally required a
Lyapunov chaos filter -- this entry isolates the Hurst-only mechanism
with the source's own trailing-stop exit instead of that entry's
different exit).

## Strategy file
`strategies/2026-09-24_hurst_regime_sma_crossover_trailstop.py`

## Grid summary (validation/grid_test.py)
`param_grid={hurst_window:[60,100,150], hurst_threshold:[0.55,0.65], trail_percent:[0.05,0.08]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2019-01-01..2026-09-01.

- total_cells=144, passed=37, pass_fraction=0.257
- by_asset_class: equity 34/72 (47.2%), crypto 3/72 (4.2%, decisive crypto reject)
- by_vol_regime: low 26/48 (54.2%), mid 11/48 (22.9%), high 0/48 (0.0%)
- best_cell: QQQ hurst_window=60/hurst_threshold=0.65/trail_percent=0.05, low-vol Sharpe 2.67
- worst_cell: ETH/USDT hurst_window=100/hurst_threshold=0.55/trail_percent=0.08, high-vol Sharpe -0.93

## Single-config validators (validation/validators.py)

### QQQ (hurst_window=60, hurst_threshold=0.65, trail_percent=0.05)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.112 | >=1.0 | YES |
| Max drawdown | 18.3% | <=25% | YES |
| Transaction cost survival (10bps, 21 trades) | net Sharpe 1.085 | >=0.5 | YES |
| Walk-forward (4 splits) | 4/4 positive (1.0) | >=0.75 | YES |
| Parameter sensitivity | relative_std 0.223 | <=0.5 | YES |

### SPY (hurst_window=100, hurst_threshold=0.55, trail_percent=0.05)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.087 | >=1.0 | YES |
| Max drawdown | 17.4% | <=25% | YES |
| Transaction cost survival (10bps, 19 trades) | net Sharpe 1.060 | >=0.5 | YES |
| Walk-forward (4 splits) | 3/4 positive (0.75) | >=0.75 | YES |
| Parameter sensitivity | relative_std 0.104 | <=0.5 | YES |

## Decision: ACCEPTED (equity: QQQ + SPY, per-symbol tuned configs)

Crypto (BTC/USDT, ETH/USDT) rejected -- grid cells decisively fail
(3/72 pass, 4.2%), consistent with the repo's general pattern of
trend-regime-filter constructions (Katsanos correlation gate, SMA
discrete-cadence gate, Lyapunov-Hurst combo) not generalizing to crypto
in this dataset.

Source: https://pyquantlab.medium.com/can-the-hurst-exponent-reliably-identify-price-trends-4aaa14ad9dda
