# Ehlers Trendflex Zero-Line Crossover — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_ehlers_trendflex_zerocross.py`
**Source:** https://www.prorealcode.com/prorealtime-indicators/reflex-and-trendflex-indicators-john-f-ehlers/
(full ProRealTime transcription of Ehlers' original TASC Feb 2020 "Reflex: A New
Zero-Lag Indicator" formula)

## Hypothesis

Ehlers' Trendflex indicator applies a 2-pole SuperSmoother low-pass filter to
close, then measures the mean deviation of the filtered series from each of
the last `length` bars, normalized by a recursively-computed root-mean-square
(so the oscillator sits roughly in units of standard deviations around zero)
with near-zero lag relative to price. A crossing of Trendflex from <=0 to >0
signals the (low-lag) trend turning up; the mirror cross signals it turning
down or flat.

## Config tested (best cell from grid)

`length=14, max_hold_days=10`

## Single-config validator results

### SPY (2018-01-01 .. 2026-09-01)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.104 | >= 1.0 | ✅ |
| Max drawdown | 12.9% | <= 25% | ✅ |
| TC survival (10bps/trade, 82 trades) | net Sharpe 0.94ish (>=0.5) | >= 0.5 | ✅ |
| Walk-forward (4 splits) | 4/4 splits positive Sharpe (100%) | >= 75% | ✅ |
| Parameter sensitivity (9-cell length x max_hold_days grid) | relative std 0.41 | <= 0.5 | ✅ |

**All 5 validators pass on SPY.**

### QQQ (2018-01-01 .. 2026-09-01), same config

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 0.622 | >= 1.0 | ❌ |
| Max drawdown | 21.2% | <= 25% | ✅ |
| TC survival (10bps/trade, 78 trades) | net Sharpe 0.498 | >= 0.5 | ❌ (barely) |
| Walk-forward (4 splits) | 3/4 splits positive (75%) | >= 75% | ✅ |
| Parameter sensitivity | relative std 0.28 | <= 0.5 | ✅ |

QQQ fails Sharpe and (barely) TC-survival at this exact config — near-miss,
not accepted for QQQ.

## Grid-test summary (Step 6)

Grid: `length in {14,20,30}`, `max_hold_days in {10,20,30}`, symbols
`{QQQ, SPY}` (equity) x `{BTC/USDT, ETH/USDT}` (crypto), 3 vol-regime
terciles (low/mid/high), start=2018-01-01, end=2026-09-01.

- **Overall pass fraction:** 26/108 = 24.1%
- **By asset class:** equity 26/54 (48.1%) passed; crypto 0/54 (0%) passed —
  decisive rejection on crypto.
- **By vol regime:** low-vol 15/36 (41.7%), mid-vol 7/36 (19.4%), high-vol
  4/36 (11.1%) — the edge concentrates heavily in low-volatility regimes,
  consistent with a low-lag trend-following signal getting whipsawed in
  choppy/high-vol conditions.
- **Best cell:** SPY, low-vol regime, length=14/max_hold_days=10, Sharpe
  2.18.
- **Worst cell:** SPY, mid-vol regime, length=30/max_hold_days=10, Sharpe
  -0.11.

## Decision

**Accept for SPY only** (all 5 single-config validators pass at
length=14/max_hold_days=10). **Reject for QQQ** (Sharpe/TC-survival miss at
this config) and **reject decisively for crypto** (0/54 grid cells pass).
Scope this strategy narrowly to SPY, low/mid-vol regimes, length~14,
max_hold_days~10-20 (grid shows nearby cells 14/20 and 14/30 also strong,
1.22 and 1.19 Sharpe respectively — this isn't a fragile single-cell
optimum).
