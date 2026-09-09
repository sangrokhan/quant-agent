# Backtest Report: Ehlers Center of Gravity (CG) Oscillator Crossover

**Strategy file:** `strategies/2026-09-10_ehlers_cg_oscillator_crossover.py`
**Date:** 2026-09-10
**Outcome:** REJECTED

## Hypothesis

Per QuantumAlgo's Center of Gravity guide
(https://www.quantum-algo.com/blog/guides/center-of-gravity-indicator-complete-guide/),
John Ehlers' Center of Gravity (CG) oscillator computes the balance point of
a rolling price window (weighted average with linearly increasing weights
toward the most recent bar), producing a near-zero-lag reversal signal. The
source's own rule: treat a raw line-turn as an early warning and a
signal-line crossover as confirmation. Tested here: long entry when CG
crosses above its one-bar-lagged signal line AND the raw CG line just
turned up; exit on the reverse crossover or a time-stop. First CG oscillator
strategy in this repo.

## Step 6 grid summary

Grid: `cg_window` in {8, 10, 20} x `max_hold_days` in {10, 20} x
QQQ/SPY/BTC/ETH x low/mid/high realized-vol terciles (72 cells,
2018-01-01 to 2024-12-31).

- pass_fraction: 0.236 (17/72)
- by_asset_class: equity 17/36, crypto 0/36 (decisive crypto fail)
- by_vol_regime: low 11/24, mid 4/24, high 2/24 (edge concentrated in
  low-vol regime, weak in high-vol)
- Best cell: cg_window=10, max_hold_days=10, QQQ, low-vol tercile,
  Sharpe 1.87. cg_window=8, max_hold_days=10 also looked strong across
  both QQQ (low 1.82, mid 1.14) and SPY (low 1.46) low/mid terciles.

## Step 7 single-config validation (cg_window=8, max_hold_days=10, full sample 2018-2024)

| Metric | QQQ | SPY | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 0.611 | 0.626 | >= 1.0 | No / No |
| Max drawdown | 0.222 | 0.201 | <= 0.25 | Yes / Yes |
| TC survival (5bps/trade) | 0.307 | 0.237 | >= 0.5 | No / No |
| Walk-forward (4 splits) | 0.75 (3/4) | 1.00 (4/4) | >= 0.75 | Yes / Yes |
| Parameter sensitivity | 0.235 | 0.368 | <= 0.5 | Yes / Yes |

Trade counts (entries only): QQQ 235, SPY 249 over ~7 years — a very high
trading frequency for a daily-bar strategy (roughly one trade every 7-8
trading days), driven by the raw CG line's sensitivity to noise despite the
line-turn+crossover double filter.

## Decision: REJECTED

Full-sample Sharpe decisively misses the 1.0 threshold on both symbols
(0.611 / 0.626), despite the tercile-conditioned grid best cells (1.4-1.9
Sharpe in low/mid-vol) looking attractive — those results don't survive
full-sample aggregation. More decisively, transaction-cost survival fails
badly on both symbols (net Sharpe 0.31/0.24 after a modest 5bps/trade cost),
because the strategy trades extremely frequently (235-249 round trips over
7 years) — the near-zero-lag sensitivity that makes the CG oscillator turn
early at genuine pivots also makes it whipsaw on noise far more often than
this repo's other oscillator-crossover strategies. The high trade frequency
alone would likely sink this strategy in live trading even before
considering the Sharpe miss.

## Source

- https://www.quantum-algo.com/blog/guides/center-of-gravity-indicator-complete-guide/
