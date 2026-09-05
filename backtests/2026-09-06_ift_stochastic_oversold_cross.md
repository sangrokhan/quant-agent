# Ehlers Inverse Fisher Transform of Stochastic — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_ift_stochastic_oversold_cross.py`
**Source:** https://toslc.thinkorswim.com/center/reference/Tech-Indicators/studies-library/G-L/IFT-StochOsc
(crediting Sylvain Vervoort's TASC Dec 2011 article)

## Hypothesis

Applying Ehlers' Inverse Fisher Transform (IFT) to a smoothed Stochastic %K
squashes the oscillator toward saturating +/-1 extremes, producing a
sharper/more decisive digital-like signal than the raw Stochastic's smooth
wandering. Long entry on IFT crossing above a negative entry_threshold
(oversold-recovery cross); exit on IFT crossing back below a positive
exit_threshold, or a max_hold_days time-stop.

## Grid-test summary (Step 6)

Grid: `stoch_window in {9,13,21}`, `entry_threshold in {-0.5,-0.3}`,
symbols `{QQQ, SPY}` (equity) x `{BTC/USDT, ETH/USDT}` (crypto), 3 vol-regime
terciles, 2018-01-01..2026-09-01.

- **Overall pass fraction:** 12/72 = 16.7%
- **By asset class:** equity 12/36 (33.3%); crypto 0/36 (0%) — decisive
  crypto rejection.
- **By vol regime:** low 5/24 (20.8%), mid 4/24 (16.7%), high 3/24 (12.5%)
  — no strong regime concentration, edge is weak/inconsistent throughout.
- **Best cell:** SPY, low-vol, stoch_window=9/entry_threshold=-0.3, Sharpe
  1.94 (single tercile, not full-sample representative).
- **Worst cell:** SPY, mid-vol, stoch_window=9/entry_threshold=-0.5, Sharpe
  -1.66.

## Single-config validator results (best grid cell config, full sample)

`stoch_window=9, entry_threshold=-0.3` (exit_threshold=0.5 default)

### SPY (2018-01-01 .. 2026-09-01)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 0.715 | >= 1.0 | ❌ |
| Max drawdown | 24.5% | <= 25% | ✅ (barely) |
| TC survival (10bps/trade, 61 trades) | net Sharpe 0.608 | >= 0.5 | ✅ |
| Walk-forward (4 splits) | 4/4 positive (100%) | >= 75% | ✅ |
| Parameter sensitivity | relative std 0.36 | <= 0.5 | ✅ |

### QQQ (2018-01-01 .. 2026-09-01), same config

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 0.529 | >= 1.0 | ❌ |
| Max drawdown | 36.9% | <= 25% | ❌ |
| TC survival (10bps/trade, 64 trades) | net Sharpe 0.445 | >= 0.5 | ❌ |
| Walk-forward (4 splits) | 4/4 positive (100%) | >= 75% | ✅ |
| Parameter sensitivity | relative std 0.15 | <= 0.5 | ✅ |

## Decision

**Reject.** Fails the primary Sharpe ratio threshold on both symbols (0.72
SPY, 0.53 QQQ, both well under 1.0) despite passing walk-forward and
parameter-sensitivity; QQQ additionally fails max drawdown and TC-survival.
Crypto rejected decisively (0/36 grid cells). The IFT-of-Stochastic
construction does not clear this repo's Sharpe bar even at its best grid
cell's full-sample config.
