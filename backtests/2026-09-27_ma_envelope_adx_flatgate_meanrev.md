# Backtest Report: MA Envelope Mean Reversion, ADX Flat-Regime Gate

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-27_ma_envelope_adx_flatgate_meanrev.py`
**KB id:** 2026-09-27-106

## Hypothesis

Source: [StockCharts ChartSchool — Moving Average Envelopes](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-average-envelopes)
(visited this iteration). The source explicitly distinguishes trend-following
use of MA Envelopes from mean-reversion use, stating the latter applies
"when the trend is relatively flat." This repo's prior unconditional MA
Envelope mean-reversion attempts (2026-09-04-065, 2026-09-06-106, both
rejected) never gated on trend flatness. This iteration adds an ADX(14) <
threshold "flat regime" gate to the same lower-band-touch-then-reclaim
mean-reversion trigger, exiting on reaching the MA, on ADX rising back above
threshold (regime flip), or a time-stop.

## Step 6 — Grid summary

Grid: `envelope_pct` in [0.03, 0.05, 0.07] x `adx_flat_threshold` in [18, 22],
symbols equity(QQQ, SPY) + crypto(BTC/USDT, ETH/USDT), 3 vol-regime terciles.
72 total cells.

- **pass_fraction: 0.097 (7/72)**
- by_asset_class: equity 1/36 passed; crypto 6/36 passed
- by_vol_regime: low 0/24, mid 4/24, high 3/24
- best_cell: envelope_pct=0.05, adx_flat_threshold=18.0, crypto ETH/USDT,
  mid-vol regime, Sharpe 1.39
- worst_cell: envelope_pct=0.03, adx_flat_threshold=22.0, crypto BTC/USDT,
  mid-vol regime, Sharpe -1.42
- Many cells (esp. envelope_pct=0.07, and equity SPY at wider pcts) had
  **zero trades** ("empty/no-trade slice") — the ADX flat-gate combined with
  a wide envelope is so restrictive that in many vol-regime slices no
  entries fire at all.

## Step 7 — Full-period validators (best config: envelope_pct=0.05, adx_flat_threshold=18.0)

| Symbol | Trades (full period) | Sharpe | MDD | TC-survival net Sharpe | Walk-forward pass_frac | Param sensitivity (rel std) |
|---|---|---|---|---|---|---|
| ETH/USDT | 2 | -0.048 (FAIL, thr 1.0) | 0.078 (PASS) | -0.050 (FAIL, thr 0.5) | 0.75 (PASS) | 2.41 (FAIL, thr 0.5) |
| BTC/USDT | 2 | 0.011 (FAIL, thr 1.0) | 0.015 (PASS) | 0.005 (FAIL, thr 0.5) | 1.00 (PASS) | 0.75 (FAIL, thr 0.5) |

The grid's promising mid-vol-regime Sharpe (~1.0-1.4) evaporates over the
full 2019-2026 period: only **2 total trades** fire per symbol over 7.5
years at this config — the AND of (envelope touch) AND (ADX below 18) is
extremely rare, so the grid's good-looking mid-vol-tercile cells were driven
by a tiny, non-representative trade count, not a robust edge. Sharpe,
transaction-cost survival, and parameter sensitivity all fail decisively.

## Step 8 — Decision: REJECTED (all symbols)

Rejected primarily on: (1) full-period Sharpe fails decisively on both
tested crypto symbols (best asset class from the grid), (2) parameter
sensitivity fails (Sharpe swings wildly, even sign-flipping, across
envelope_pct 0.03/0.05/0.07 at trade counts this low), (3) transaction-cost
survival fails. Equity (QQQ/SPY) was even weaker in the grid (1/36 pass) and
not pursued to full validation. The ADX flat-gate, while conceptually sound
per the source, is too restrictive when conjoined with an envelope touch —
entries become too rare (2 trades/7.5yr) for the strategy to be a usable
signal at any tested threshold combination.

**Notes for future loops:** if revisiting this angle, consider loosening the
gate (ADX percentile-based rather than absolute threshold, or using
Choppiness Index instead of ADX) or dropping the max_hold_days constraint
which may be truncating what would otherwise be more, smaller wins.
