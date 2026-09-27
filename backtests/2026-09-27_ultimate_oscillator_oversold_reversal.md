# Ultimate Oscillator Oversold Reversal — Backtest Report

**Strategy file:** `strategies/2026-09-27_ultimate_oscillator_oversold_reversal.py`
**Date:** 2026-09-27
**Outcome:** REJECTED

## Hypothesis

Source: https://gainium.io/help/ultimate-oscillator (read 2026-09-27 via browser_exec,
web_extract cannot render this JS page's help-center content).

The Ultimate Oscillator (Larry Williams, 1976) combines buying-pressure /
true-range ratios over three lookback periods (fast=7, mid=14, slow=28,
weighted 4:2:1) into a single 0-100 momentum oscillator designed to reduce
false reversal signals vs. single-period oscillators (RSI, Stochastic).
Source's disclosed rule (Strategy 1 "Overbought/Oversold Reversal"): enter
long when UO crosses below 30 (oversold), exit when UO crosses back above 50
(midline, momentum fading). This repo implements the long-only half (no
shorts per SAFETY.md), plus a 15-day time-stop for consistency with other
mean-reversion strategies here.

First Ultimate Oscillator strategy in this repo (0 prior hits for "Ultimate
Oscillator"/"UO" in `strategies_index.jsonl`).

## Single-config validators (QQQ, oversold_level=30, exit_level=45, max_hold_days=15)

Note: best grid cell used exit_level=45 (source's raw 50 midline cell failed
in the grid), so validators ran on the grid's actual best-performing config.

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.833 | >= 1.0 | **FAIL** |
| Max drawdown | 0.077 | <= 0.25 | PASS |
| Transaction cost survival (10bps/trade, 7 trades) | 0.809 | >= 0.5 | PASS |
| Walk-forward (4 splits) | 1.0 (4/4 splits Sharpe>0) | >= 0.75 | PASS |
| Parameter sensitivity (relative std across oversold_level x exit_level, max_hold=15) | 0.588 | <= 0.5 | **FAIL** |

## Step 6 grid summary (oversold_level x exit_level x max_hold_days, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3)

- Total cells: 216, passed: 7, **pass_fraction = 0.0324**
- By asset class: equity 7/108 passed; **crypto 0/108 passed** (decisive fail)
- By vol regime: low 0/72, mid 3/72, high 4/72 (edge concentrated in
  higher-vol regimes only, and even there very thin)
- Best cell: QQQ, oversold_level=30, exit_level=45, max_hold_days=15,
  high-vol regime, Sharpe 1.637
- Worst cell: SPY, oversold_level=25, exit_level=50, max_hold_days=10,
  high-vol regime, Sharpe -0.787
- Passing configs cluster narrowly around exit_level=45 (source's own 50
  midline underperforms in this repo's window) and oversold_level in
  {30, 35} on QQQ/SPY only, each only 1/3 vol-regime cells.

## Decision: REJECTED

Full-sample Sharpe (0.833) misses the 1.0 threshold and parameter
sensitivity is high (relative std 0.588 > 0.5) — the strategy's apparent
edge in the grid is concentrated in a narrow slice (QQQ/SPY, high-vol
regime, exit_level=45 specifically) rather than being robust across the
parameter neighborhood the source itself proposed (exit_level=50 midline).
Crypto is a decisive fail across the entire grid (0/108). Walk-forward and
MDD both pass, and trade count is thin (7 trades over ~7.5 years) which
likely also contributes to the high parameter-sensitivity relative std.

Worth a future revisit note: try widening the grid to test if a shorter
UO period set (e.g. fast=5/mid=10/slow=20, an alternate commonly-cited
setting) or an added trend/vol-regime gate stabilizes the edge, similar to
the fix pattern used for other near-miss oscillator strategies in this repo.
