# Backtest Report: Fractional-Kelly-Criterion Sizing Overlay (2026-09-08)

**Status: REJECTED (decisively)** — strategy file kept in `strategies/` as
a record of a rejected attempt, not a live strategy.

## Hypothesis

Per JournalX "Kelly Criterion Position Sizing: Why Full Kelly Breaks
Traders" (https://journalx.app/blog/kelly-criterion-position-sizing), Kelly's
`f* = (b*p - q) / b` gives the growth-optimal fraction of capital to risk;
fractional Kelly (25-50% of full) is recommended to capture most of the
growth at a fraction of the drawdown. Adapted: size an SMA(200) trend
signal using a rolling no-lookahead estimate of the strategy's own trailing
win-rate/payoff ratio, scaled by `kelly_fraction`.

## Single-config validator results (best grid config: `kelly_fraction=0.25`, `default_weight=0.5`)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Walk-forward | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| QQQ | 0.274 ❌ | 0.045 ✅ | -0.117 ❌ | 0.5 ❌ | 0.609 ❌ | 49 |
| SPY | 0.083 ❌ | 0.038 ✅ | -0.357 ❌ | 0.5 ❌ | 1.210 ❌ | 76 |

## Grid test summary

`param_grid={kelly_fraction:[0.25,0.5,1.0], default_weight:[0.5,1.0]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`
(2018-01-01 to 2026-09-01), 72 total cells.

- Overall pass_fraction: 0.236 (17/72 cells) — looks superficially similar
  to CPPI's 0.25, but this is misleading (see below)
- By asset class: equity 17/36 passed, crypto 0/36
- By vol regime: low 12/24, mid 5/24, high 0/24
- Best cell: SPY, low-vol, Sharpe 2.195
- Worst cell: SPY, high-vol, Sharpe -1.047

## Decision

**Reject decisively.** The grid's Sharpe+MDD-only per-cell check
overstates viability — the FULL validator suite fails badly on both
equities: Sharpe far below threshold, net Sharpe after costs NEGATIVE,
walk-forward only 2/4 splits positive, and parameter sensitivity wildly
unstable (relative std 0.61 QQQ / 1.21 SPY). The only passing validator
(max_drawdown) is an artifact of chronic under-sizing, not genuine risk
control: Kelly's `f*` computed from a noisy trailing daily-return-as-trade
estimate is usually small/near-zero, so the strategy holds tiny positions
most of the time.

**Root-cause lesson for future position-sizing iterations:** Kelly's `p`/`b`
framework assumes discrete win/loss TRADE outcomes, not a continuous daily
return series relabeled as wins/losses day-by-day. This structural mismatch
— not a parameter-tuning issue — likely explains the walk-forward and
parameter-sensitivity failures. A genuine re-test would need actual
discrete trade entries/exits (e.g. from the trend filter's own entry/exit
events) rather than treating every trend-active day as an independent
"trade".
