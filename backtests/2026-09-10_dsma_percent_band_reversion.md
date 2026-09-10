# 2026-09-10 — Ehlers DSMA Percent-Band Mean Reversion (REJECTED)

## Hypothesis

Per John Ehlers' Deviation-Scaled Moving Average (TASC July 2018), formula
per https://www.prorealcode.com/prorealtime-indicators/deviation-scaled-moving-average-dsma/
and strategy rule per https://www2.wealth-lab.com/WL5Wiki/TASCJul2018.ashx:
DSMA is an adaptive EMA whose alpha scales with a SuperSmoother-filtered,
RMS-normalized "standard deviations from the mean" measure. Source's own
disclosed strategy (explicitly framed "counter-trend for kicks"): buy when
close crosses a percentage below the 40-period DSMA, exit when close
crosses a percentage above it.

Strategy file: `strategies/2026-09-10_dsma_percent_band_reversion.py`

## Grid summary (entry_pct in [0.015,0.02,0.03] x exit_pct in [0.015,0.02], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- 3/72 cells passed (pass_fraction 0.042), all 3 on equity — crypto 0/36 decisively.
- By vol regime: low 2/24, mid 1/24, high 0/24.
- Best cell: QQQ, entry_pct=0.02, exit_pct=0.015, low-vol tercile, Sharpe 1.39.
- Worst cell: QQQ, entry_pct=0.02, exit_pct=0.015, mid-vol tercile, Sharpe -0.25.

## Full-sample quick check (entry_pct=0.02, exit_pct=0.015, 2017-01-01..2026-09-01)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) |
|---|---|---|---|
| QQQ | 0.045 (FAIL, thr 1.0) | 0.391 (FAIL, thr 0.25) | 0.006 (FAIL, thr 0.5) |
| SPY | 0.170 (FAIL) | 0.280 (FAIL) | 0.132 (FAIL) |

## Decision: REJECT

Decisive rejection on the full sample — every validator fails for both
symbols, and the grid's isolated low-vol-tercile passes do not generalize
(the source itself flagged this as an explicitly "counter-trend for kicks"
strategy, i.e. not the DSMA's core intended trend-following use case). The
0.39 max drawdown on QQQ is particularly bad, well above the 0.25
threshold. This confirms the source's own framing: DSMA is best suited for
trend-following, and using it as a mean-reversion band (as tested here) is
a weaker application that the source itself only offered "for kicks" without
claiming it works well. Full validator suite (walk-forward, parameter
sensitivity) skipped as unnecessary given the decisive full-sample failure.
A future loop could instead test DSMA in its INTENDED trend-following role
(price crosses above/below DSMA with the DSMA itself sloping up/down) as a
more promising follow-up.
