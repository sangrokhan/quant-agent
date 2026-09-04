# Backtest Report: Chaikin Oscillator Zero-Line Cross + 200d Trend Filter

**Strategy file:** `strategies/2026-09-04_chaikin_osc_trend_filter.py`
**Date:** 2026-09-04
**Source:** https://www.quantifiedstrategies.com/chaikin-oscillator-trading-strategy/
(retrieved via browser_exec fallback after web_search DDGS/Yahoo TLS failure)

## Hypothesis

Source reports a naive Chaikin Oscillator (CO = EMA(fast,ADL) - EMA(slow,ADL))
zero-line-cross strategy is weak in isolation on the S&P 500 (CAGR ~2.4%/20yr
at optimized 10/20 params). This iteration tests whether adding this repo's
standard 200-day SMA trend filter (only take the long zero-cross signal when
price > SMA200) improves on that weak baseline, consistent with prior findings
in this repo (2026-09-01-001 failed specifically due to lack of regime
filtering).

## Full-sample single-config metrics (SPY, QQQ; fast=3, slow=20)

| Symbol | Sharpe | Threshold | Pass | MDD | Threshold | Pass |
|--------|--------|-----------|------|-----|-----------|------|
| SPY    | 0.466  | 1.0       | No   | 0.205 | 0.25 | Yes |
| QQQ    | 0.829  | 1.0       | No   | 0.227 | 0.25 | Yes |

(fast=10/slow=10 config produced a degenerate 1-trade/near-zero-exposure
"infinite Sharpe" artifact -- excluded as non-representative; grid-best
non-degenerate config is fast=3/slow=20.)

## Grid test summary (fast_window x slow_window x 4 symbols x 3 vol terciles = 48 cells)

- pass_fraction: **16.7%** (8/48)
- by_asset_class: equity 8/24 (33%), crypto 0/24 (0%)
- by_vol_regime: low 6/16 (38%), mid 2/16 (13%), high 0/16 (0%)
- best_cell: SPY, fast=3/slow=20, low-vol regime, Sharpe 2.93
- worst_cell: QQQ, fast=3/slow=10, high-vol regime, Sharpe -0.98

## Validators run

- Sharpe ratio: **FAIL** on both SPY (0.47) and QQQ (0.83) at full-sample,
  best-non-degenerate grid config -- neither clears the 1.0 threshold.
- Max drawdown: PASS on both (SPY 20.5%, QQQ 22.7%, both < 25% budget).
- Transaction-cost-survival / walk-forward / parameter-sensitivity: **skipped**
  per RESEARCH_LOOP.md Step 7 -- a full-sample Sharpe failure on both tested
  equity symbols is already decisive; grid pass_fraction (16.7%) additionally
  confirms this doesn't hold up broadly.

## Decision: REJECTED

Sharpe fails on both equity symbols even at the grid-optimal config; crypto
is a complete washout (0/24 grid cells). The 200d trend filter did keep MDD
within budget (consistent with this repo's convention that trend/vol-regime
filters reduce drawdown effectively), but confirms the source's own finding:
the Chaikin Oscillator zero-line-cross signal itself has weak/no
risk-adjusted edge, even with a trend-filter overlay. Matches the source's
own headline conclusion (CAGR ~2.4%, "not very predictive on its own").

Future idea (from source): combining CO overbought/oversold readings (RSI
applied to the oscillator itself, or RSI on the underlying instrument) with
CO produced modestly better (though still weak, ~17-18% MDD) results in the
source's own tests -- worth a future iteration if revisited, rather than the
pure zero-cross variant tested here.
