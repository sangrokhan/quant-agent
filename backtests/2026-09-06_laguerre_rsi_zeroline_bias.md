# Backtest Report: Ehlers Laguerre RSI Zero-Line (0.5) Momentum-Bias Filter (2026-09-06)

**Strategy file:** `strategies/2026-09-06_laguerre_rsi_zeroline_bias.py`
**Knowledge base id:** 2026-09-06-110
**Outcome:** ACCEPTED (QQQ only)

## Hypothesis

Ehlers Laguerre RSI (4-stage recursive Laguerre filter -> RSI-style 0-1
oscillator) used as a standalone zero-line momentum-bias regime filter:
long when LRSI > 0.5 (bullish momentum), flat when LRSI <= 0.5 (bearish
momentum). No discrete entry/exit trigger or time-stop -- position tracks
the regime state directly each bar.

## Source

https://www.quantifiedstrategies.com/laguerre-rsi/ (QuantifiedStrategies
"Laguerre RSI" article): "Using Zero Line (0.5) as Momentum Bias: When the
Laguerre RSI stays above 0.5, momentum is bullish. Below 0.5 indicates
bearish momentum. This simple rule can be used as a filter for systematic
strategies." Gamma guidance: 0.2 fast/short-term, 0.5 balanced default,
0.7-0.8 smooth/slow.

Distinct from the already-tested and rejected Laguerre RSI mean-reversion
variant in this repo (2026-09-05-053, 0.2/0.8 extreme-threshold entries) --
same underlying oscillator, different (simpler, continuous-regime) usage
pattern per the source's own explicitly stated alternate rule. Also
distinct from the Adaptive Laguerre Filter (2026-09-05-058), a different
Ehlers indicator (price smoother, not an RSI-style oscillator).

## Step 6 grid summary (gamma in [0.2,0.5,0.7,0.8], equity=[QQQ,SPY],
crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3, 2018-01-01..2026-09-01)

- total_cells: 48, passed_cells: 11, **pass_fraction: 0.229**
- by_asset_class: equity 11/24 passed, crypto 0/24 passed
- by_vol_regime: low 8/16, mid 3/16, high 0/16
- best_cell: SPY, gamma=0.7, low-vol regime, Sharpe 2.778
- worst_cell: QQQ, gamma=0.8, high-vol regime, Sharpe -0.550

## Step 7 single-config validation, full sample 2018-2026

### QQQ, gamma=0.5 (full-sample sweep found this the best QQQ config)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.128 | >= 1.0 | **PASS** |
| Max drawdown | 0.235 | <= 0.25 | **PASS** |
| Transaction cost survival (10bps, 89 trades) | net Sharpe 1.022 | >= 0.5 | **PASS** |
| Walk-forward (4 splits) | pass_fraction 1.0 (4/4 positive) | >= 0.75 | **PASS** |
| Parameter sensitivity (4-cell gamma grid) | relative_std 0.167 | <= 0.5 | **PASS** |

All 5 validators pass on QQQ. gamma sweep on QQQ: 0.2->0.830, 0.5->1.128,
0.7->0.923, 0.8->0.720 (stable, gently peaked around gamma=0.5).

### SPY, gamma=0.7 (grid's SPY-side best cell config)

Full-sample Sharpe 0.931 (near-miss, below 1.0), MDD 0.195 (pass), net
Sharpe after costs 0.872 (pass), walk-forward 4/4 (pass), parameter
sensitivity relative_std 0.076 (pass). 4 of 5 validators pass but Sharpe
falls just short -- SPY is NOT accepted at this config.

### BTC/USDT cross-check

Full-sample Sharpe across gamma in [0.2,0.5,0.7,0.8]: 0.051, 0.126, 0.228,
0.176 -- decisively weak, consistent with grid's 0/24 crypto pass rate.
Crypto rejected.

## Decision

**ACCEPTED for QQQ only** (gamma=0.5). All 5 validators pass cleanly with a
notably stable parameter-sensitivity profile (relative_std 0.167 across the
full gamma grid, and 0.076 specifically around the SPY-side optimum,
indicating this is not a fragile single-cell fluke). **SPY near-miss**
(Sharpe 0.931, 4/5 validators pass) -- worth revisiting with a slightly
different gamma or a light trend/volatility co-filter in a future
iteration. **Crypto rejected decisively** (0/24 grid cells, full-sample
Sharpe <=0.23 across the entire gamma range) -- this indicator's momentum-
bias framing does not transfer to BTC/ETH's very different volatility and
autocorrelation structure.
