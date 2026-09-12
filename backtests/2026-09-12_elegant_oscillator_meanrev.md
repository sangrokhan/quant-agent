# Backtest Report: Ehlers Elegant Oscillator (Inverse Fisher Transform) Mean Reversion

**Strategy file:** `strategies/2026-09-12_elegant_oscillator_meanrev.py`
**Source:** John F. Ehlers, TASC February 2022. Formula reproduced from
https://financial-hacker.com/the-inverse-fisher-transform/ (fully
disclosed C code).

## Hypothesis

The Elegant Oscillator (EO) converts a normalized 2-bar price derivative
into the +/-1 range via the Inverse Fisher Transform, SuperSmoother-
smoothed. Long-only adaptation: long on an EO valley below -threshold,
exit on EO crossing back above 0 or a time-stop. The source's own test
was only 7 trades on SPY 2020-2021 (positive but thin); this repo ran a
broader grid.

## Full-sample parameter search (length x {10,20,30}, smooth_length x {10,20}, threshold x {0.3,0.5,0.7}, max_hold_days x {5,10,20})

| Symbol | Best config | Best Sharpe |
|---|---|---|
| QQQ | length=10, smooth_length=10, threshold=0.3, max_hold_days=5 | 1.252 |
| SPY | length=10, smooth_length=10, threshold=0.3, max_hold_days=5 | 0.999 (rounds to ~1.0) |

## Single-config validator results (best shared config: length=10, smooth_length=10, threshold=0.3, max_hold_days=5)

### QQQ

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.507 | >= 1.0 |
| Max drawdown | PASS | 0.134 | <= 0.25 |
| Transaction cost survival (10bps/trade, 196 trades) | PASS | net Sharpe 1.059 | >= 0.5 |
| Walk-forward (4 manual contiguous splits) | PASS | 4/4 (100%) | >= 75% |
| Parameter sensitivity (length x smooth_length grid) | **FAIL** | rel. std 1.043 | <= 0.5 |

### SPY

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.202 | >= 1.0 |
| Max drawdown | PASS | 0.150 | <= 0.25 |
| Transaction cost survival (10bps/trade, 202 trades) | PASS | net Sharpe 0.751 | >= 0.5 |
| Walk-forward (4 manual contiguous splits) | PASS | 4/4 (100%) | >= 75% |
| Parameter sensitivity | PASS | rel. std 0.362 | <= 0.5 |

QQQ fails parameter sensitivity (the strategy's edge is highly concentrated
at length=10; longer lengths collapse or reverse Sharpe sign, producing a
high relative std across the length/smooth_length grid). SPY passes all 5.

## Crypto screening (length=10, smooth_length=10, threshold=0.3, max_hold_days=5, full sample)

| Symbol | Sharpe |
|---|---|
| BTC/USDT | 0.703 |
| ETH/USDT | 0.669 |

Both decisively below the 1.0 threshold — crypto rejected.

## Decision: ACCEPT (SPY only); REJECT (QQQ — parameter sensitivity fail); REJECT (crypto — decisive)

SPY passes every validator with a shared config. QQQ has a higher raw
Sharpe (1.507) but fails parameter sensitivity — its edge is fragile to
the length/smooth_length choice, so it is not accepted despite the
attractive headline Sharpe. Crypto is decisively rejected. Scope this
strategy to SPY only.
